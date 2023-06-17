 # Creating base image
FROM python:3.10.6

 # Setting up the working directory
WORKDIR /fog-app

 # Install dependencies
COPY server_code/requirements.txt .
RUN pip install -r requirements.txt
RUN apt-get update && apt-get install -y libzmq3-dev
RUN pip install --upgrade pyzmq
RUN pip install pyzmq[zmqasync]
RUN apt-get update && apt-get install -y net-tools


 # Copying the source code
COPY server_code/ .

# Exposing the port
EXPOSE 37328

 # Run the server code
 CMD ["python3", "cloud_server.py"]