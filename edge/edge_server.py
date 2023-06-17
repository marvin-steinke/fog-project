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

    def __init__(self, bootstrap_servers: str, input_topic: str, output_topic: str, db_handler: dbHandler, cloud_node_address) -> None:
        
        self.logger = logging.getLogger("EdgeServer")
        self.cloud_node_address = cloud_node_address        
        db_file = os.path.join(os.path.dirname(__file__), '..', 'local.db')
        self.db_handler = db_handler

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
        
    '''
    # cannot be used yet
    def _maintain_connection_thread(self):
        """Continually try to establish a connection with the cloud node."""
        while not self.shutdown:
            if not self.connected:
                self.logger.info("Attempting to connect to the cloud node...")
                self.connected = self._connect_to_cloud_node()
                if self.connected:
                    self.logger.info("Successfully connected to the cloud node.")
                else:
                    self.logger.error("Failed to connect to the cloud node. Retrying...")
                    time.sleep(5)  # Wait before trying to connect again

    '''
    
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
            for _ in range(10):
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
                            self._send_to_server(node_id, average)
                        
    
                        values.clear()
    
    def _connect_to_server(self) -> None:
        """
        Establishes connection to the cloud node and performs ping-pong communication.
        """
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect(self.cloud_node_address)
        socket.send(b'ping')
        print("message sent")

        # Wait for the pong reply
        pong_reply = socket.recv()
        if pong_reply == b'pong':
            print("Received pong from the server. Connection is successful.")
            self.cloud_connected = True       
        else:
            print("Received unknown reply from the server.")

        socket.close()
        context.term()

    def _send_to_server(self, node_id, average):
        try:
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.connect(self.cloud_node_address)

            request_data = {
                'node_id': node_id,
                'average': average
            }
            request = json.dumps(request_data).encode('utf-8')
            socket.send(request)

            response = socket.recv()
            print(response.decode())

            socket.close()
            context.term()

        except zmq.ZMQError as e:
            print(f"Error occurred while sending data to the server: {e}")

        '''
        # cannot be used yet

        if self.connected:
            self.send_to_cloud_node({"node_id": node_id, "average_power": average})
        else:
            self.logger.warning("Not connected to the cloud node. Stored average power locally.")
        '''
        # self._send_to_server(node_id, average)
            

    '''
    # not for know but soon
                        
    def _send_to_server(self, node_id, average):
        try:
            self.socket.connect(self.server_address)

            request_data = {
                'node_id': node_id,
                'average': average
            }
            request = json.dumps(request_data).encode('utf-8')
            self.socket.send(request)

            response = self.socket.recv()
            print(response.decode())

        except zmq.ZMQError as e:
            print(f"Error occurred while sending data to the server: {e}")
        finally:
            self.socket.disconnect(self.server_address)
    '''
                        
    '''
    # cannot be used yet
    
    def send_to_cloud_node(self, data):
        """Sends data from the producer thread to the cloud node and waits for the acknowledgment.

        Args:
            data (_type_): dict values for node_id and average_power
        """
        try:
            request = json.dumps(data).encode('utf-8')
            self.client.send(request)

            remaining_retries = 3
            while True:
                if self.client.poll(2500) & zmq.POLLIN:
                    reply = self.client.recv()
                    if reply == b'ACK':
                        break
                    else:
                        self.logger.error("Server reply negative: %s", reply)
                else:
                    remaining_retries -= 1
                    if remaining_retries == 0:
                        self.logger.warning("Cloud node seems to be offline, retrying request")
                        return False

                    self.logger.info("Cloud node seems to be offline, retrying request")

                    self.client.setsockopt(zmq.LINGER, 0)
                    self.client.close()
                    self.logger.info("Reconnecting to cloud node")
                    self.client = self.context.socket(zmq.REQ)
                    self.client.connect(self.cloud_node_address)
                    self.logger.info("Resending request %s", request)
                    self.client.send(request)

            return True
        except Exception as e:
            self.logger.error("Error occurred while sending data to the cloud node: %s", e)
            return False
    '''
    
    '''
    # cannot be used yet    
    def _send_unsent_data(self):
        """
        Fetches unsent data from the database, sends it to the cloud, and updates
        their sent status.
        """
        unsent_data = self.db_handler.get_unsent_power_averages()
        for row in unsent_data:
            id, node_id, average, timestamp = row
            data = {"node_id": node_id, "average_power": average}
            sent_successfully = self.send_to_cloud_node(data)
            if sent_successfully:
                self.db_handler.update_power_average(id)
            else:
                self.logger.error("Failed to send unsent data with id {} to the cloud node.".format(id))
    '''
    def run(self) -> None:
        """Starts the consumer and producer threads, and sets the ready
        attribute to True."""
        try:
            self.consumer_thread = Thread(target=self._consumer_thread)
            self.producer_thread = Thread(target=self._producer_thread)
            self.consumer_thread.start()
            self.producer_thread.start()
            self.ready = True
            self._connect_to_server()
        except Exception as e:
            self.logger.error("Error occurred while running the EdgeServer: %s", e)

    def stop(self) -> None:
        """Stops the consumer and producer threads, and sets the ready
        attribute to False."""
        self.shutdown = True
        self.consumer_thread.join()
        self.producer_thread.join()
        self.consumer.close()
        self.producer.close()
        self.ready = False
        #db_handler.truncate_table("power_averages")
        self.db_handler.close_connection()


if __name__ == '__main__':
    bootstrap_servers = 'localhost:9092'
    input_topic = 'input_topic'
    output_topic = 'output_topic'
    cloud_node_address = 'tcp://localhost:37329'
    db_handler = dbHandler('local.db')
    edge_server = EdgeServer(bootstrap_servers, input_topic, output_topic, db_handler, cloud_node_address)
    edge_server.run()
    