# Creating base image
FROM python:3.10.6

# Setting up the working directory
WORKDIR /fog-app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN apt-get update && apt-get install -y libzmq3-dev
RUN apt-get update && apt-get install -y net-tools
RUN apt-get update && apt-get install -y redis-server
RUN pip install pynng
RUN pip install asyncio

# Copying the source code
COPY . /fog-app

# Exposing the ports
EXPOSE 37329
EXPOSE 63270

# Specify the command to execute the server script
CMD ["python3", "cloud_server.py"]
