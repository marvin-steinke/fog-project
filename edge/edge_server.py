import json
import time
from threading import Lock, Thread
from typing import Dict
from collections import defaultdict
from kafka import KafkaConsumer, KafkaProducer
from local_db.db_operations import dbHandler
import logging
import os
import pynng

# Define the logger
logger = logging.getLogger()
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)


class EdgeServer:
    """Server that processes streaming data, computes average power values for
    nodes in a 30-second window, and publishes results.

    The `EdgeServer` class is a server that interfaces with Apache Kafka to
    process streaming data. It consumes messages from a specified input Kafka
    topic, performs computations on the data (specifically, computes the
    average power value for each node within a 30-second window), and then
    publishes the results to a specified output Kafka topic. The server
    operates using two concurrent threads for consuming and producing data. It
    can be started with the `run()` method and stopped safely with the `stop()`
    method.

    Args:
        bootstrap_servers (str): The Kafka bootstrap servers.
        input_topic (str): The input Kafka topic to consume messages from.
        output_topic (str): The output Kafka topic to produce messages to.
        db_handler (dbHandler): The dbHandler object to handle db operations.
    """

    def __init__(self, bootstrap_servers: str, input_topic: str, output_topic: str, db_handler: dbHandler) -> None:
        
        self.logger = logging.getLogger("EdgeServer")
        
        # db stuff
        db_file = os.path.join(os.path.dirname(__file__), '..', 'local.db')
        self.db_handler = db_handler
        self.db_lock = Lock()
        
        # connection flags
        self.connection_lock = Lock()
        self.server_socket = None
        self.cloud_connected = False
        self.unsent_data = None
        
        #sockets
        self.server_socket = pynng.Pub0()
        self.server_socket.dial('tcp://localhost:63271')
        
        # sensor simulation
        self.consumer = KafkaConsumer(
            input_topic,
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda x: json.loads(x.decode('utf-8')))

        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda x: json.dumps(x).encode('utf-8'))

        self.output_topic = output_topic
        self.lock = Lock()
        self.data: Dict[str, list] = defaultdict(list)
        self.ready = False
        self.shutdown = False


    def _consumer_thread(self) -> None:
        """Consumes messages from the input Kafka topic and stores the values
        in the data attribute."""
        while not self.shutdown:
            messages = self.consumer.poll(timeout_ms=1000)
            for message in messages.values():
                node_id = message[0].value['node_id']
                power_value = message[0].value['power_value']
                with self.lock:
                    self.data[node_id].append(power_value)


    def _producer_thread(self) -> None:
        """Periodically calculates averages of the power values and sends them
        to the output Kafka topic or fetches unsent and unacknowledged data from the local db and sends it to the cloud node."""
        self.unsent_data = []
        while not self.shutdown:
            for _ in range(5):
                if self.shutdown:
                    return
                time.sleep(1)
                
            with self.lock:
                for node_id, values in self.data.items():
                    if values:
                        average = sum(values) / len(values)
                        print("Node ID:", node_id)
                        print("Average Power:", average)

                        # Send real-time data to the cloud if connected and insert it into the db
                        id = self.db_handler.insert_power_average(node_id, average)
                        
                    with self.connection_lock:
                        if self.cloud_connected:
                            if not self._send_to_server(id, node_id, average):
                                self.unsent_data.append((id, node_id, average, time.time()))
                                continue
                            # Send unsent and unacknowledged data to the cloud if the connection is reestablished
                            if self.unsent_data:
                                for data in list(self.unsent_data):  # Make a copy of the list to avoid issues with modifying it during iteration
                                    id, node_id, average, _ = data
                                    if not self._send_to_server(id, node_id, average):
                                        continue
                                    logging.info(f"Sent unsent data with id {id} to the cloud node.")
                                    self.unsent_data.remove(data)
                            self.unsent_data = []
                        else:
                            # Fetch unsent and unacknowledged data if the list is empty
                            temp_unsent_data = self.db_handler.fetch_lost_data()
                            if temp_unsent_data:
                                for data in temp_unsent_data:
                                    if data not in self.unsent_data:
                                        self.unsent_data.append(data)
                            logging.error("UNSENT DATA: " + str(self.unsent_data))
                    values.clear()

                        

    def connection_thread(self) -> None:
        """
        Thread that continually checks for connection and sets the cloud_connected flag.
        """
        with pynng.Pair0() as socket:
            socket.dial('tcp://localhost:63270')

            while not self.shutdown:
                try:
                    socket.send(b'heartbeat')
                    response = socket.recv()
                    with self.connection_lock:
                        if response != b'ack':
                            print("No ack received")
                            self.cloud_connected = False
                        else:
                            self.cloud_connected = True
                except (pynng.exceptions.ConnectionRefused, ValueError, Exception) as e:
                    with self.connection_lock:
                        self.cloud_connected = False
                    logging.error(f"Could not connect to the server: {e}")
        

    def _send_to_server(self, id: int, node_id: str, average: float) -> bool:
        """Send the computed average values to the cloud server."""
        try:
            request_data = {
                'id': id,
                'node_id': node_id,
                'average': average
            }
            request = json.dumps(request_data).encode('utf-8')
            self.server_socket.send(request)
            logging.info("Sent data to the server.")
            self.db_handler.update_sent_flag(id)
            return True
        except pynng.NNGException as e:
            logging.error(f"Error occurred while sending data to the server: {e}")
            return False


    def _receive_from_server(self) -> bool:
        """
        Continuously receives data from the server.

        Returns:
            bool: True if the data was successfully received, False otherwise.
        """
        while not self.shutdown:
            if not self.cloud_connected:
                time.sleep(1)
                continue
            try:
                with pynng.Sub0() as socket:
                    socket.listen('tcp://localhost:63272')
                    socket.subscribe(b'')
                    while True:
                        try:
                            message = socket.recv()
                            if message:
                                try:
                                    data = message.decode('utf-8')
                                    extracted_number = int(data.split(':')[1].strip())
                                    print(f"Received Sequence ID from the server: {data}")
                                    with self.db_lock:
                                        self.db_handler.update_sequence_number(extracted_number)
                                        self.db_handler.update_to_ack(extracted_number)
                                except UnicodeDecodeError:
                                    print("Failed to decode received message")
                        except pynng.exceptions.TryAgain:
                            continue
            except pynng.NNGException as e:
                print(f"Error occurred while receiving data from the server: {e}")
            if self.shutdown:
                break


    def run(self) -> None:
        """Starts the consumer and producer threads, and sets the ready
        attribute to True."""
        
        try:
            self.consumer_thread = Thread(target=self._consumer_thread)
            self.producer_thread = Thread(target=self._producer_thread)
            self.connection_check_thread = Thread(target=self.connection_thread)
            self.receive_server_acks = Thread(target=self._receive_from_server)
            self.consumer_thread.start()
            self.producer_thread.start()
            self.connection_check_thread.start()
            self.receive_server_acks.start()
            self.ready = True
        
        except Exception as e:
            self.logger.error("Error occurred while running the EdgeServer: %s", e)

    def stop(self) -> None:
        """Stops the consumer and producer threads, and sets the ready attribute to False."""
        self.shutdown = True
        try:
            if self.consumer_thread.is_alive():
                self.consumer_thread.join()
            if self.producer_thread.is_alive():
                self.producer_thread.join()
            if self.connection_check_thread.is_alive():
                self.connection_check_thread.join()
            if self.receive_server_acks.is_alive():
                self.receive_server_acks.join()

            self.consumer.close()
            self.producer.close()

            if self.server_socket:
                self.server_socket.close()
        except KeyboardInterrupt:
            pass
        finally:
            self.ready = False
            self.db_handler.close_connection()

if __name__ == '__main__':
    
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    bootstrap_servers = 'localhost:9092'
    input_topic = 'input_topic'
    output_topic = 'output_topic'
    db_handler = dbHandler('local.db')
    edge_server = EdgeServer(bootstrap_servers, input_topic, output_topic, db_handler)
    edge_server.run()
