import json
import logging
import pynng
import asyncio
import redis
import time
import random
import subprocess

logging.basicConfig(level=logging.INFO)

cache_host = '127.0.0.1'
redis_port = 6379
redis_db = 0

def establish_cache_connection():
    """Establishes a connection to the Redis cache server.

    Returns:
        redis.Redis: A Redis cache connection object.

    Raises:
        redis.RedisError: If an error occurs connecting to the Redis cache server.
    """
    try:
        cache = redis.Redis(host=cache_host, port=redis_port, db=redis_db)
        logging.info("Connected to Redis cache server.")
        logging.info(f"Ready to accept Connections.")
        return cache
    except redis.RedisError as e:
        logging.error(f"Error connecting to Redis cache server: {e}")
        raise

cache = establish_cache_connection()

async def receive_heartbeat():
    """Handles the receipt of heartbeats from an edge server."""
    with pynng.Rep0() as heartbeat_socket:
        heartbeat_socket.listen('tcp://0.0.0.0:63270')
        last_heartbeat_time = time.time()

        while True:
            try:
                message = await asyncio.wait_for(heartbeat_socket.arecv(), timeout=5)
                if message == b'heartbeat':
                    last_heartbeat_time = time.time()
                    await heartbeat_socket.asend(b'ack')
                else:
                    logging.error("Received an invalid message from the edge server")
            except asyncio.TimeoutError:
                current_time = time.time()
                if current_time - last_heartbeat_time > 5:
                    logging.error("No connection: Heartbeat not received")
            except Exception as e:
                logging.error(f"Error while receiving heartbeat: {e}")

async def receive_data():
    """Handles the receipt of data from an edge server."""
    with pynng.Sub0() as data_socket:
        data_socket.listen('tcp://0.0.0.0:63271')
        data_socket.subscribe(b'')
        while True:
            try:
                request = await data_socket.arecv()
                request_data = json.loads(request.decode('utf-8'))
                id = request_data.get('id', 'Unknown')
                node_id = request_data.get('node_id', 'Unknown')
                average = request_data.get('average', 'Unknown')
                logging.info(f"Received data from edge server - id: {id}")
                await plz_data(id)
                cache_data(id, average)
            except pynng.exceptions.TryAgain:
                await asyncio.sleep(1)
            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode JSON data: {e}")
            except Exception as e:
                logging.error(f"Error while receiving data: {e}")

async def plz_data(id):
    """Sends postal code back to the edge server.

    Args:
        id: The unique identifier for which the postal code is to be generated.
    """
    with pynng.Pub0() as ack_socket:
        try:
            ack_socket.dial('tcp://0.0.0.0:63272')
            plz = generate_plz(str(id))
            postal_code = f"PLZ for id: {id} - PLZ: {plz}".encode('utf-8')
            await ack_socket.asend(postal_code)
            logging.info(f"Sent PLZ for id: {id} - PLZ: {plz}")
        except pynng.exceptions.TryAgain:
            logging.error("Connection not available yet")
        except Exception as e:
            logging.error(f"Error while sending postal code back to edge: {e}")

def generate_plz(id):
    """Generates a postal code based on the given id.

    Args:
        id (str): The unique identifier for which the postal code is to be generated.

    Returns:
        str: A postal code based on the given id.
    """
    random_numbers = ''.join(str(random.randint(0, 9)) for _ in range(4))
    return f'{id[:3]}{random_numbers}'


def cache_data(id, node_average):
    """Cache data in redis server.

    Args:
        id (str): The unique identifier of the data to be cached.
        node_average (str): The average node data to be cached.
    """
    try:
        cache.set(id, node_average)
        logging.info(f"Cached data - id: {id}, node_average: {node_average}")
    except Exception as e:
        logging.error(f"Error while caching data: {e}")


async def main():
    """Main function that runs data fetcher, and creates tasks for receiving data and heartbeats."""
    # start flask backend
    data_fetcher_process = subprocess.Popen(["python3", "../client/data_fetcher.py"],
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)

    receive_task = asyncio.create_task(receive_data())
    heartbeat_task = asyncio.create_task(receive_heartbeat())

    await asyncio.gather(receive_task, heartbeat_task)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    logging.info("KeyboardInterrupt: Stopping the server.")
