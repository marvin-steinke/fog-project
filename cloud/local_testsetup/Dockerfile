# Creating base image
FROM python:3.10.6

# Setting up the working directory
WORKDIR /fog-app

# Install dependencies
COPY server_code/requirements.txt .
RUN pip install -r requirements.txt
RUN apt-get update && apt-get install -y libzmq3-dev
RUN pip install --upgrade pyzmq
RUN apt-get update && apt-get install -y net-tools
RUN apt-get update && apt-get install -y redis-server

# Copying the source code
COPY server_code/ .

# Exposing the port
EXPOSE -p 37328

# Run Redis in the background
CMD redis-server --daemonize yes

# Run the server code
CMD ["python3", "cloud_server.py"]
