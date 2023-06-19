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
    #... [insert the entire EdgeServer class here] ...

if __name__ == '__main__':
    bootstrap_servers = 'localhost:9092'
    input_topic = 'input_topic'
    output_topic = 'output_topic'
    cloud_node_address = 'tcp://localhost:37329'
    db_file = os.path.join(os.path.dirname(__file__), '..', 'local.db')
    db_handler = dbHandler(db_file)
    
    # create the schema before starting the Edge server
    db_handler.create_schema()

    edge_server = EdgeServer(bootstrap_servers, input_topic, output_topic, db_handler, cloud_node_address)
    edge_server.run()

    print("Running for 10 seconds...")
    time.sleep(10)

    print("Now, manually disconnect the network or stop the cloud server to simulate a disconnection...")
    print("Waiting for 30 seconds...")
    time.sleep(30)

    print("You can now reconnect the network or start the cloud server again...")
    print("Running for another 10 seconds to test reconnection...")
    time.sleep(10)

    edge_server.stop()
    print("Test completed.")

    # check the unsent data in the database
    unsent_data = db_handler.get_unsent_power_averages()
    print(f"Unsent data: {unsent_data}")
    
    # clear data from db after test
    db_handler.truncate_table('power_averages')
    db_handler.close_connection()
