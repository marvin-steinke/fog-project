import zmq
import json


def handle_client(server):
    while True:
        request = server.recv()
        try:
            data = json.loads(request.decode())
            print("Received data from node_id:", data['node_id'])
            print("Average value:", data['average'])
            
            response = "Received data successfully"
            server.send(response.encode())
        except json.JSONDecodeError:
            print("Received unknown message")

    
def main():
    context = zmq.Context()
    server = context.socket(zmq.REP)
    server.bind("tcp://*:37329")

    # Start the server to handle incoming requests
    handle_client(server)

    # Close the socket when finished
    server.close()
    context.term()

if __name__ == '__main__':
    main()
