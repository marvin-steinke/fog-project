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
import itertools

# Set variables for messaging actions of the edge node
# Inspired by the Lazy Pirate server from the ZMQ guide

REQUEST_TIMEOUT = 2500
REQUEST_RETRIES = 3 # might need to be handled dynamically

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
    """

    def __init__(self, bootstrap_servers: str, input_topic: str, output_topic: str, db_handler:dbHandler) -> None:
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
        
        # Use the db_handler argument to initialize the db_handler attribute
        self.db_handler = db_handler

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
                    
    """
    The following functions extend kafka's producer thread by enabling reliable messaging. This is achieved by the usage of a local db
    and a reliable messaing protocol towards the destiantion node (cloud node).

    """

    def _producer_thread(self) -> None:
        """Periodically calculates averages of the power values and sends them
        to the output Kafka topic."""
        while not self.shutdown:
            for _ in range(30):
                if self.shutdown:
                    return
                time.sleep(1)
            with self.lock:
                for node_id, values in self.data.items():
                    if values:
                        average = sum(values) / len(values)
                        print(average)
                        
                        # Initial step for real-time data stream: Sending the calculated average power value to the output topic.
                        self.producer.send(self.output_topic, {"node_id": node_id, "average_power": average})
                        
                        # Step 1: Writing the calculated average power value into the local database.
                        # Note: This operation is designed to ensure data persistence in case of connectivity issues.
                        id = self.db_handler.insert_power_average(node_id, average)
                        
                        # Step 2: Attempting to send the data to the cloud node.
                        # In the case of successful transmission, the 'sent' flag in the local database 
                        # is updated to 1 (indicating successful transmission).
                        # In case of failure, the 'sent' flag remains 0, enabling us to identify and 
                        # re-attempt transmission of unsent data when the connection is restored.
                        sent = self.send_to_cloud_node({"node_id": node_id, "average_power": average})
                        
                        # Updating the 'sent' flag in the database based on whether the data was successfully sent or not
                        if sent:
                            self.db_handler.update_power_average(id)
                        
                        values.clear()
    
    def send_to_cloud_node(self, data):
        """Sends data from the producer thread to the cloud node.

        Args:
            data (_type_): dict values for node_id and average_power
        """
        self.client.connect(self.clode_node_address) # needs to be specified in config.ini
        
        request = json.dumps(data).encode('utf-8')
        logging.info("Sending request %s", request)
        self.client.send(request)
        
        remaining_retries = REQUEST_RETRIES
        while True:
            if (self.client.poll(REQUEST_TIMEOUT) & zmq.POLLIN) != 0:
                reply = self.client.recv()
                if reply == b' ACK':
                    logging.info("Cloud node received request")
                    remaining_retries = REQUEST_RETRIES
                    break
                else:
                    logging.error("Server reply negative: %s", reply)
                    
            remaining_retries -= 1
            logging.warning("Cloud node seems to be offline, retrying request")
        
            # Close and remove the socket before trying connection establishment again
            self.client.setsockopt(zmq.LINGER, 0)
            self.client.close()
            if remaining_retries == 0:
                logging.error("FATAL: Cloud node seems to be offline, abandoning")
            break
        
            logging.info("Reconnecting to cloud node")
        
        # Create new connection to the cloud node
        self.client = self.context.socket(zmq.REQ)
        self.client.connect(self.clode_node_address)
        logging.info("Resending request %s", request)
        self.client.send(request)
        
    def recover_unsent_data(self):
        # Fetch data in db that is flagged with 'sent' = 0
        unsent_data = self.db_handler.get_unsent_power_averages
        
        # Try to send unsent data to the cloud node
        for id, node_id, average, sent, timestamp in unsent_data:
            sent = self.send_to_cloud_node({"node_id": node_id, "average_power": average})
            # Update the database if sent successfully
            if sent:
                self.db_handler.update_power_average(id)
                
    def _recovery_thread(self) -> None:
        """Periodically checks for unsent data and tries to resend it to the clode node."""
        while not self.shutdown:
            self.recover_unsent_data()
            # Sleep for 30 seconds between attempts
            for _ in range(30):
                if self.shutdown:
                    return
                time.sleep(1)
                
    """
    Failover handling implementation is done.
    """
    
    def run(self) -> None:
        """Starts the consumer and producer threads, and sets the ready
        attribute to True."""
        self.consumer_thread = Thread(target=self._consumer_thread)
        self.producer_thread = Thread(target=self._producer_thread)
        self.consumer_thread.start()
        self.producer_thread.start()
        self._recovery_thread.start()
        self.ready = True

    def stop(self) -> None:
        """Stops the consumer and producer threads, and sets the ready
        attribute to False."""
        self.shutdown = True
        self.consumer_thread.join()
        self.producer_thread.join()
        self._recovery_thread.join()
        self.consumer.close()
        self.producer.close()
        self.ready = False


if __name__ == '__main__':
    bootstrap_servers = 'localhost:9092'
    input_topic = 'input_topic'
    output_topic = 'output_topic'
    db_handler = dbHandler('test.db')
    edge_server = EdgeServer(bootstrap_servers, input_topic, output_topic, db_handler)
    edge_server.run()

