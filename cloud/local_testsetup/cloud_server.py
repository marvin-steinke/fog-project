import zmq
import json
import redis
import logging
from typing import Any

logging.basicConfig(level=logging.INFO)
# Connect to redis
r = redis.Redis(host='redis', port=6379, db=0)
  
def handle_client(server: zmq.Socket) -> None:
    """Handle client's requests and responses.

    Args:
        server (zmq.Socket): The server socket instance.
    """
    while True:
        request = server.recv()
        try:
            data = json.loads(request.decode())
            logging.info(f"Received data from node_id: {data.get('node_id', 'Unknown')}")
            logging.info(f"Average value: {data.get('average', 'Unknown')}")
            try:
                # cache the received data
                r.hset('node_data', data['node_id'], json.dumps(data))
                response = "Received data successfully"
                server.send(response.encode())
            except json.JSONDecodeError:
                logging.error("Received unknown message")
        except json.JSONDecodeError:
            logging.error("Failed to decode JSON request")
    
def main():
    """Main function to initialize the server and handle the edge servers requests."""
    context = zmq.Context()
    server = context.socket(zmq.REP)
    server.bind("tcp://*:37329")
    
    logging.info("Server started listening at tcp port://*:37329")
    # Start the server to handle incoming requests
    handle_client(server)

    # Close the socket when finished
    server.close()
    context.term()
    logging.info("Server closed successfully.")

if __name__ == '__main__':
    main()
