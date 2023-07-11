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
import configparser


# Define the logger
logger = logging.getLogger()
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)


class EdgeServer:
    """Server that processes streaming data and publishes results.

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

        config = configparser.ConfigParser()
        config.read('config.ini')
        gcp_node_address = config.get("Server", "gcp_node")

        # destination config
        self.gcloud_node_heartbeat = f"tcp://{gcp_node_address}:63270"
        self.gcloud_node_data = f"tcp://{gcp_node_address}:63271"

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
        """Consumes messages from input Kafka topic and stores the values."""
        while not self.shutdown:
            messages = self.consumer.poll(timeout_ms=1000)
            for message in messages.values():
                node_id = message[0].value['node_id']
                power_value = message[0].value['power_value']
                with self.lock:
                    self.data[node_id].append(power_value)

    def _producer_thread(self) -> None:
        """Periodically calculates averages of the power values."""
        while not self.shutdown:
            for _ in range(5):
                if self.shutdown:
                    return
                time.sleep(1)

            with self.lock:
                for node_id, values in self.data.items():
                    if values:
                        average = sum(values) / len(values)
                        with self.db_lock:
                            id = self.db_handler.insert_power_average(node_id, average)
                        print("Power Data queued:", id)
                        

    def _connection_thread(self) -> None:
        """Thread that continually checks for connection."""
        logging.info("Connecting to cloud node...")
        while not self.shutdown:
            try:
                connection_alive = False
                heartbeat_socket = pynng.Req0()
                heartbeat_socket.dial(self.gcloud_node_heartbeat, block=False)
                heartbeat_socket.send_timeout = 1000
                try:
                    heartbeat_socket.send(b'heartbeat')
                    response = heartbeat_socket.recv()
                    connection_alive = response == b'ack'
                    if connection_alive:
                        logging.info("Connection to the server is established.")
                    else:
                        logging.info("Server is not responding...")
                except pynng.exceptions.Timeout:
                    logging.error("Cannot connect to server. Data transmission is halted...")
                    connection_alive = False
                time.sleep(3)
            except Exception as e:
                logging.error(f"Error occurred in the connection thread: {str(e)}")
                connection_alive = False
            with self.cloud_connected_condition:
                self.cloud_connected = connection_alive
                self.cloud_connected_condition.notify_all()
        heartbeat_socket.close()
        

    def _data_sender(self):
        """Send the computed average values to the cloud server."""
        self.server_socket = pynng.Req0()
        self.server_socket.dial(self.gcloud_node_data)
        while not self.shutdown:
            with self.cloud_connected_condition:
                self.cloud_connected_condition.wait_for(lambda: self.cloud_connected)

                if not self.cloud_connected:
                    continue

                latest_data_ids = set()
                new_data = self.db_handler.fetch_latest_data()
                if not new_data:
                    continue

                # Send new data
                for entry in new_data:
                    id, node_id, average = entry
                    latest_data_ids.add(id)

                    request_data = {
                        'id': id,
                        'node_id': node_id,
                        'average': average
                    }
                    request = json.dumps(request_data).encode('utf-8')

                    with self.cloud_connected_condition:
                        if not self.cloud_connected:
                            logging.info("Connection lost. Buffering data for sending.")
                            break
                        try:
                            self.server_socket.send(request)
                            logging.info(f"Queued Data buffered for sending to the server: {id}")
                            with self.db_lock:
                                self.db_handler.update_sent_flag(id)
                            response = self.server_socket.recv()
                            self._handle_response_from_server(response)
                        except pynng.NNGException as e:
                            logging.error(f"Error occurred while sending data to the server: {e}")
                            break

                # Send lost data if not already sent
                lost_data = self.db_handler.fetch_lost_data()
                for entry in lost_data:
                    id, node_id, average, _ = entry
                    if id not in latest_data_ids:
                        request_data = {
                            'id': id,
                            'node_id': node_id,
                            'average': average
                        }
                        request = json.dumps(request_data).encode('utf-8')

                        with self.cloud_connected_condition:
                            if not self.cloud_connected:
                                logging.info("Connection lost. Buffering data for sending.")
                                break
                            try:
                                self.server_socket.send(request)
                                logging.info(f"Queued Data buffered for sending to the server: {id}")
                                with self.db_lock:
                                    self.db_handler.update_sent_flag(id)
                                response = self.server_socket.recv()
                                self._handle_response_from_server(response)
                            except pynng.NNGException as e:
                                logging.error(f"Error occurred while sending data to the server: {e}")
                                break


    def _handle_response_from_server(self, message) -> None:
        """Handle the response from the server.

        Args:
            message: The response message received from the server.

        Returns:
            None.
        """
        try:
            data = message.decode('utf-8')
            match = re.match(r"PLZ for id: (\d+) - PLZ: (\d+)", data)
            if match:
                id, postal_code = map(int, match.groups())
                print(f"Received Post Code from the server: {data}")
                with self.db_lock:
                    self.db_handler.update_postal_code(id, postal_code)
                    self.db_handler.update_to_ack(id)
            else:
                print(f"Failed to parse message: {data}")
        except UnicodeDecodeError:
            print("Failed to decode received message")


    def run(self) -> None:
        """Starts consumer, producer, connection_check and data_send threads."""

        try:
            self.consumer_thread = Thread(target=self._consumer_thread)
            self.producer_thread = Thread(target=self._producer_thread)
            self.connection_check_thread = Thread(target=self._connection_thread)
            self.data_send_thread = Thread(target=self._data_sender)
            self.connection_check_thread.start()
            self.consumer_thread.start()
            self.producer_thread.start()
            self.data_send_thread.start()
            self.ready = True

        except Exception as e:
            self.logger.error("Error occurred while running the EdgeServer: %s", e)

    def stop(self) -> None:
        """Stops consumer, producer, connection_check, and data_send threads."""
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
            self.consumer.close()
            self.producer.close()

            if self.server_socket:
                self.server_socket.close()
        except KeyboardInterrupt:
            pass
        finally:
            self.ready = False
            self.db_handler.close_connection()

