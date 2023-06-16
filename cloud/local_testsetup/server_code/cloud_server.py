import zmq
import asyncio
import zmq.asyncio

async def handle_client(server):
    while True:
        # Wait for the client's ping message
        request = await server.recv()

        if request == b'ping':
            # Reply with a pong message to acknowledge the connection
            await server.send(b'pong')
            print("Received: ping")
            print("Reply sent: pong")
        else:
            # Handle other requests or conditions as needed
            await server.send(b'unknown')  # Send an appropriate reply
            print("Received unknown message")

async def main():
    context = zmq.asyncio.Context()
    server = context.socket(zmq.REP)
    server.bind("tcp://*:37329")

    # Start the server to handle incoming requests
    while True:
        # Wait for the client connection
        client = await server.recv()
        asyncio.create_task(handle_client(server))

if __name__ == '__main__':
    asyncio.run(main())
