import json
import logging
import pynng
import asyncio
import redis

logging.basicConfig(level=logging.INFO)

cache_host = '127.0.0.1'
redis_port = 6379
redis_db = 0

def establish_cache_connection():
    """
    Establishes a connection to the Redis cache server.

    Returns:
        redis.Redis: Redis cache connection object.

    Raises:
        redis.RedisError: If there is an error connecting to the Redis cache server.
    """
    try:
        cache = redis.Redis(host=cache_host, port=redis_port, db=redis_db)
        logging.info("Connected to Redis cache server.")
        logging.info(f"Ready to accept Connections.")
        return cache
    except redis.RedisError as e:
        logging.error(f"Error connecting to Redis cache server: {e}")
        raise

# connect to cache 
cache = establish_cache_connection()

async def receive_heartbeat():
    """
    Receives heartbeat messages from edge servers.
    """
    with pynng.Pair0() as heartbeat_socket:
        heartbeat_socket.listen('tcp://localhost:63270')
        while True:
            message = await heartbeat_socket.arecv()
            if message == b'heartbeat':
                await heartbeat_socket.asend(b'ack')
        

async def receive_data():
    """
    Receives data from edge servers.
    """
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
                logging.info(f"Received data from edge server - id: {id}, node_id: {node_id}, average: {average}")
                ack_data(id)
                cache_data(id, average)
            except pynng.exceptions.TryAgain:
                await asyncio.sleep(1)
            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode JSON data: {e}")
            except Exception as e:
                logging.error(f"Error while receiving data: {e}")

def ack_data(id):
    """
    Sends acknowledgement for received data to edge servers.

    Args:
        id (str): ID of the received data.
    """
    with pynng.Pub0() as ack_socket:
        try:
            ack_socket.dial('tcp://localhost:63272')
            sequence_number = f"Acknowledgement for receive id: {id}".encode('utf-8')
            ack_socket.send(sequence_number)
            logging.info(f"Sent acknowledgement for id: {id}") 
        except pynng.exceptions.TryAgain:
            logging.error("Connection not available yet")
        except Exception as e:
            logging.error(f"Error while sending acknowledgement: {e}")

def cache_data(id, node_average):
    """
    Caches the received data.

    Args:
        id (str): ID of the received data.
        node_average (float): Average value associated with the received data.
    """
    try:
        cache.set(id, node_average)  
        logging.info(f"Cached data - id: {id}, node_average: {node_average}")
    except redis.RedisError as e:
        logging.error(f"Error while caching data: {e}")
    except Exception as e:
        logging.error(f"Error while caching data: {e}")

async def main():
    """
    Main function to run the server.
    """
    receive_task = asyncio.create_task(receive_data())
    heartbeat_task = asyncio.create_task(receive_heartbeat())

    await asyncio.gather(receive_task, heartbeat_task)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    logging.info("KeyboardInterrupt: Stopping the server.")
