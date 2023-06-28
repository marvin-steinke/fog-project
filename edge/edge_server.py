import json
import time
from threading import Lock, Thread
from typing import Dict
from collections import defaultdict
from kafka import KafkaConsumer, KafkaProducer
from local_db.db_operations import dbHandler
import logging
import zmq
import os
import pynng

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
        
        # connection flags
        self.cloud_connected = False
        # self.sent_successfully = False
        # self.acknowledged_successfully = False
        
        # simulation environment
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
        to the output Kafka topic."""
        while not self.shutdown:
            for _ in range(5):
                if self.shutdown:
                    return
                time.sleep(1)
            with self.lock:
                for node_id, values in self.data.items():
                    if values:
                        average = sum(values) / len(values)
                        print(average)
                        print("Node ID:", node_id)
                        print("Average Power:", average)

                        id = self.db_handler.insert_power_average(node_id, average)
                        #send to cloud if connected and insert in db
                        if self.cloud_connected:
                             self._send_to_server(id, node_id, average)

                        values.clear()


    def connection_thread(self) -> None:
        """
        Thread that continually checks for connection and sets the cloud_connected flag.
        """
        prev_connection_status = False
        while not self.shutdown and not self.cloud_connected:
            try:
                with pynng.Pair0() as socket:
                    socket.dial('tcp://localhost:63270')
                    socket.send(b'heartbeat')
                    response = socket.recv()
                    if response != b'ack':
                        raise ValueError("Unexpected response")
                    self.cloud_connected = True
                    print("Successfully connected to the server.")
            except (pynng.exceptions.Timeout, ValueError) as e:
                self.cloud_connected = False
                print(f"Failed to connect to the server. Error: {e}. Retrying in 2 seconds...")
                time.sleep(2)
            else:
                if not prev_connection_status:
                    # If the connection was restored, send unsent data
                    self._send_unsent_data()
                prev_connection_status = True
        time.sleep(5)


    def _send_to_server(self, id: int, node_id: str, average: float) -> None:
        """Send the computed average values to the cloud server."""
        if not self.cloud_connected:
            return False
        try:
            socket = pynng.Pub0()
            socket.dial('tcp://localhost:63271')
        
            request_data = {
                'id': id,
                'node_id': node_id,
                'average': average
            }
            request = json.dumps(request_data).encode('utf-8')
            socket.send(request)
            print("Sent data to the server.")
            self.db_handler.update_sent_flag(id)
            socket.close()
            return True
        except pynng.NNGException as e:
            print(f"Error occurred while sending data to the server: {e}")
            return False
    
    
    def _send_unsent_data(self) -> None:
        """Fetches unsent data from the local db, sends it to the cloud, and updates the status flag in the row."""
        while not self.shutdown:
            unsent_data = self.db_handler.get_unsent_power_averages()
            unacknowledged_data = self.db_handler.get_unacknowledged_power_averages()
            for row in unsent_data and unacknowledged_data:
                id, node_id, average, timestamp = row
                data = {"node_id": node_id, "average_power": average}
                sent_successfully = self._send_to_server(id, node_id, average)
                ack_successfull = self.receive_server_acks()
                # if sent_successfully and acknowledged_suss:
                #     self.db_handler.update_sent_flag(id)
                # else:
                    #self.logger.error(f"Failed to send unsent data with id {id} to the cloud node.")
            time.sleep(3)


    def _receive_from_server(self) -> None:
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
        """Stops the consumer and producer threads, and sets the ready
        attribute to False."""
        self.shutdown = True
        self.consumer_thread.join()
        self.connection_check_thread.join()
        self.producer_thread.join()
        self.consumer.close()
        self.producer.close()
        self.ready = False
        self.db_handler.truncate_table("power_averages")
        self.db_handler.close_connection()
        
if __name__ == '__main__':
    bootstrap_servers = 'localhost:9092'
    input_topic = 'input_topic'
    output_topic = 'output_topic'
    db_handler = dbHandler('local.db')
    edge_server = EdgeServer(bootstrap_servers, input_topic, output_topic, db_handler)
    edge_server.run()
