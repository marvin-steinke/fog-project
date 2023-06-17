import socket

def find_available_port():
    # Create a socket object
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to an available port with a random IP address
    sock.bind(('localhost', 0))

    # Get the assigned port number
    port = sock.getsockname()[1]

    # Close the socket
    sock.close()

    return port

# Usage
available_port = find_available_port()
print(f"Available TCP port: {available_port}")
