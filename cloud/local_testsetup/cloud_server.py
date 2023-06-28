import json
import redis
import logging
from typing import Any
import pynng
import asyncio

logging.basicConfig(level=logging.INFO)
# Connect to Redis
r = redis.Redis(host='redis', port=6379, db=0)

async def receive_heartbeat():
    with pynng.Pair0() as heartbeat_socket:
        heartbeat_socket.listen('tcp://localhost:63270')
        while True:
            message = await heartbeat_socket.arecv()
            if message == b'heartbeat':
                print('Received heartbeat message')

# def handle_client(server: zmq.Socket) -> None:
#     """Handle client's requests and responses.

#     Args:
#         server (zmq.Socket): The server socket instance.
#     """
#     while True:
#         try:
#             request = server.recv()
#         except AttributeError:
#             logging.warning("Server socket closed. Rebinding the server socket.")
#             server.unbind("tcp://*:37329")
#             server.bind("tcp://*:37329")
#             continue

#         if request == b'ping':
#             server.send(b'pong')
#             continue
#         try:
#             data = json.loads(request.decode())
#             node_id = data.get('node_id', 'Unknown')
#             average = data.get('average', 'Unknown')
#             logging.info(f"Received data from node_id: {node_id}")
#             logging.info(f"Average value: {average}")

#             # Cache the received data
#             r.hset('node_data', node_id, json.dumps(data))
#             response = "Received data successfully"
#             server.send(response.encode())
#         except json.JSONDecodeError:
#             logging.ecrror("Failed to decode JSON message")

async def main():
    await receive_heartbeat()
    print(f'Server is running')

asyncio.run(main())