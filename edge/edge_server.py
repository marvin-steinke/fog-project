import json
import time
import threading
from threading import Lock, Thread
from typing import Dict
from collections import defaultdict
from kafka import KafkaConsumer, KafkaProducer
from local_db.db_operations import dbHandler
import logging
import os
import pynng
import re

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
        self.server_socket = None
        self.cloud_connected = False
        self.cloud_connected_condition = threading.Condition()
        
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

                        #with self.db_lock:
                        id = self.db_handler.insert_power_average(node_id, average)
    
                        
    def _connection_thread(self) -> None:
        """
        Thread that continually checks for connection and sets the cloud_connected flag.
        """
        with pynng.Pair0() as heartbeat_socket:
            heartbeat_socket.dial('tcp://localhost:63270')
            heartbeat_socket.recv_timeout = 1000  # setting timeout to 1 second

            while not self.shutdown:
                try:
                    heartbeat_socket.send(b'heartbeat')
                    response = heartbeat_socket.recv()

                    should_be_connected = response == b'ack'
                    logging.info(f"Connection status: {should_be_connected}")

                except pynng.exceptions.Timeout:
                    logging.error("Connection lost with the server.")
                    should_be_connected = False
                except Exception as e:
                    logging.error(f"Could not connect to the server: {e}")
                    should_be_connected = False

                with self.cloud_connected_condition:
                    print("connection therad entered with condition")
                    print("cloud connected:", self.cloud_connected)
                    print("should be connected:", should_be_connected)
                    if (self.cloud_connected != should_be_connected) or (self.cloud_connected == True):
                        self.cloud_connected = should_be_connected
                        self.cloud_connected_condition.notify_all()
                        
                time.sleep(3)


    def _data_sender(self):
        """Send the computed average values to the cloud server."""
        while not self.shutdown:
            with self.cloud_connected_condition:
                #print("entered data sender and with condition")
                self.cloud_connected_condition.wait_for(lambda: self.cloud_connected)
                #print("woke up from wait")
                data = self.db_handler.fetch_latest_data()
                if not data:  # if there's no data to be sent
                    continue
                #print("data to be sent:", data) 
                try:
                    for entry in data:            
                        id, node_id, average = entry
                        request_data = {
                            'id': id,
                            'node_id': node_id,
                            'average': average
                        }
                        request = json.dumps(request_data).encode('utf-8')
                        self.server_socket.send(request)
                        #logging.info("Sent data to the server.")
                        #with self.db_lock:
                        self.db_handler.update_sent_flag(id)
                except pynng.NNGException as e:
                    logging.error(f"Error occurred while sending data to the server: {e}")
                    


    def _receive_from_server(self) -> None:
        """
        Continuously receives data from the server.

        Returns:
            None.
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
                                    # Extract ID and postal code from message and call db method
                                    data = message.decode('utf-8')
                                    match = re.match(r"PLZ for id: (\d+) - PLZ: (\d+)", data)
                                    if match:
                                        id, postal_code = map(int, match.groups())
                                        print(f"Received Post Code from the server: {data}")
                                        with self.db_lock:
                                            self.db_handler.update_postal_code(postal_code)
                                            self.db_handler.update_to_ack(id)
                                    else:
                                        print(f"Failed to parse message: {data}")
                                except UnicodeDecodeError:
                                    print("Failed to decode received message")
                        except pynng.exceptions.TryAgain:
                            continue
            except pynng.NNGException as e:
                print(f"Error occurred while receiving data from the server: {e}")
            if self.shutdown:
                break


    def run(self) -> None:
        """Starts the consumer, producer, connection_check and data_send threads,
        and sets the ready attribute to True."""
        
        try:
            self.consumer_thread = Thread(target=self._consumer_thread)
            self.producer_thread = Thread(target=self._producer_thread)
            self.connection_check_thread = Thread(target=self._connection_thread)
            self.data_send_thread = Thread(target=self._data_sender)
            self.receive_plz = Thread(target=self._receive_from_server)
            
            self.connection_check_thread.start()
            time.sleep(5)
            self.consumer_thread.start()
            self.producer_thread.start()
            
            self.data_send_thread.start()
            self.receive_plz.start()
            self.ready = True
        
        except Exception as e:
            self.logger.error("Error occurred while running the EdgeServer: %s", e)

    def stop(self) -> None:
        """Stops the consumer, producer, connection_check, and data_send threads, 
        and sets the ready attribute to False."""
        self.shutdown = True
        try:
            if self.consumer_thread.is_alive():
                self.consumer_thread.join()
            if self.producer_thread.is_alive():
                self.producer_thread.join()
            if self.connection_check_thread.is_alive():
                self.connection_check_thread.join()
            if self.data_send_thread.is_alive():
                self.data_send_thread.join()
            if self.receive_plz.is_alive():
                self.receive_plz.join()

            self.consumer.close()
            self.producer.close()

            if self.server_socket:
                self.server_socket.close()
        except KeyboardInterrupt:
            pass
        finally:
            self.ready = False
            self.db_handler.close_connection()
