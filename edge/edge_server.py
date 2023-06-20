import json
import time
from threading import Lock, Thread
from typing import Dict
from collections import defaultdict
from kafka import KafkaConsumer, KafkaProducer
from local_db.db_operations import dbHandler
import logging
import sys
import zmq
import os

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
        cloud_node_address (str): The address of the cloud node.
    """

    def __init__(self, bootstrap_servers: str, input_topic: str, output_topic: str, db_handler: dbHandler, cloud_node_address: str) -> None:
        
        self.logger = logging.getLogger("EdgeServer")
        self.cloud_node_address = cloud_node_address        
        db_file = os.path.join(os.path.dirname(__file__), '..', 'local.db')
        self.cloud_connected = False
        self.db_handler = db_handler
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.RCVTIMEO = 2000

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
                        # send to cloud if connected and insert in db   
                        if self.cloud_connected:
                            self._send_to_server(id, node_id, average)
                        
                        values.clear()
    
    def connection_thread(self) -> None:
        """Thread that continually checks for connection and sets the cloud_connected flag."""
        while not self.shutdown:
            if not self.cloud_connected:
                try:
                    self.socket.connect(self.cloud_node_address)
                    self.socket.send(b'ping')
                    response = self.socket.recv()
                    if response != b'pong':
                        raise ValueError("Unexpected response")
                    self.cloud_connected = True
                    print("Successfully connected to the server.")
                except (zmq.ZMQError, ValueError) as e:
                    self.cloud_connected = False
                    print(f"Failed to connect to the server. Error: {e}. Retrying in 2 seconds...")
                    time.sleep(2)
            else:
                time.sleep(5)


    def _send_to_server(self, id: int, node_id: str, average: float) -> None:
        """Send the computed average values to the cloud server."""
        if not self.cloud_connected:
            return False
        try:
            request_data = {
                'id': id,
                'node_id': node_id,
                'average': average
            }
            request = json.dumps(request_data).encode('utf-8')
            self.socket.send(request)
            response = self.socket.recv()
            print(response.decode())
            self.db_handler.update_power_average(id)
            return True
        except zmq.ZMQError as e:
            print(f"Error occurred while sending data to the server: {e}")
            return False
        
    def _send_unsent_data(self) -> None:
        """Fetches unsent data from the local db, sends it to the cloud, and updates the status flag in the row.
        """
        while not self.shutdown:
            unsent_data = self.db_handler.get_unsent_power_averages()
            for row in unsent_data:
                id, node_id, average, timestamp = row
                data = {"node_id": node_id, "average_power": average}
                sent_successfully = self._send_to_server(id, node_id, average)
                if sent_successfully:
                    self.db_handler.update_power_average(id)
                else:
                    self.logger.error("Failed to send unsent data with id {} to the cloud node.".format(id))
            time.sleep(3)

    def _receive_from_server(self) -> None:
        while not self.shutdown:
            if not self.cloud_connected:
                time.sleep(1)
                continue

            try:
                self.socket.setsockopt(zmq.RCVTIMEO, 2000)  # Set timeout to 2000 milliseconds
                try:
                    events = self.socket.poll(timeout=2000)  # Poll the socket for events
                    if events & zmq.POLLIN:  # Check if there is incoming data
                        data = self.socket.recv()
                        if data:
                            try:
                                data = json.loads(data)
                                if 'id' in data:
                                    self.db_handler.update_power_average(data['id'])
                                else:
                                    print("Received data doesn't contain 'id' field")
                            except json.JSONDecodeError:
                                print("Received data is not in valid JSON format")
                except zmq.Again:
                    print("Timeout occurred while receiving data from the server")
                    continue
            except zmq.ZMQError as e:
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
            self.unsent_data_thread = Thread(target=self._send_unsent_data)
            self._receive_from_server_thread = Thread(target=self._receive_from_server)
            self.consumer_thread.start()
            self.producer_thread.start()
            self.connection_check_thread.start()
            self.unsent_data_thread.start()
            self._receive_from_server_thread.start()
            self.ready = True
        except Exception as e:
            self.logger.error("Error occurred while running the EdgeServer: %s", e)

    def stop(self) -> None:
        """Stops the consumer and producer threads, and sets the ready
        attribute to False."""
        self.shutdown = True
        self.consumer_thread.join()
        self.connection_check_thread.join()
        self.unsent_data_thread.join()
        self._receive_from_server_thread.join()  
        self.producer_thread.join()
        self.consumer.close()
        self.producer.close()
        self.ready = False
        time.sleep(30) # to check db entries :)
        self.db_handler.truncate_table("power_averages")
        self.db_handler.close_connection()


if __name__ == '__main__':
    bootstrap_servers = 'localhost:9092'
    input_topic = 'input_topic'
    output_topic = 'output_topic'
    cloud_node_address = 'tcp://localhost:37329'
    db_handler = dbHandler('local.db')
    edge_server = EdgeServer(bootstrap_servers, input_topic, output_topic, db_handler, cloud_node_address)
    edge_server.run()
    