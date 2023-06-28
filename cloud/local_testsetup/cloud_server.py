import json
import logging
import pynng
import asyncio
import redis

logging.basicConfig(level=logging.INFO)

# Assign the redis cache:
cache = redis.Redis(import redis

# Connect to Redis
r = redis.Redis(host='redis', port=6379)

async def receive_heartbeat():
    with pynng.Pair0() as heartbeat_socket:
        heartbeat_socket.listen('tcp://localhost:63270')
        while True:
            message = await heartbeat_socket.arecv()
            if message == b'heartbeat':
                print('Received heartbeat message')
                await heartbeat_socket.asend(b'ack')
                print('Sent ack message')
                
async def receive_data():
    with pynng.Sub0() as data_socket:
        data_socket.listen('tcp://localhost:63271')
        data_socket.subscribe(b'')
        while True:
            try:
                request = await data_socket.arecv()
                request_data = json.loads(request.decode('utf-8'))
                id = request_data.get('id', 'Unknown')
                node_id = request_data.get('node_id', 'Unknown')
                average = request_data.get('average', 'Unknown')
                print(f"Received data from edge server - id: {id}, node_id: {node_id}, average: {average}")
                ack_data(id)
            except pynng.exceptions.TryAgain:
                await asyncio.sleep(1)

def ack_data(id):
    with pynng.Pub0() as ack_socket:
        try:
            ack_socket.dial('tcp://localhost:63272')
            sequence_number = f"Acknowledgement for receiv id: {id}".encode('utf-8')
            ack_socket.send(sequence_number)
            print(f"Sent acknowledgement for id: {id}")
        except pynng.exceptions.TryAgain:
            print("Connection not available yet")
            
def cache_data(id, node_average):
    

async def main():
    receive_task = asyncio.create_task(receive_data())
    heartbeat_task = asyncio.create_task(receive_heartbeat())

    await asyncio.gather(receive_task, heartbeat_task)

asyncio.run(main())



