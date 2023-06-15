 # Creating base image
FROM python:3.10.6

 # Setting up the working directory
WORKDIR /fog-app

 # Install dependencies
COPY server_code/requirements.txt .
RUN pip install -r requirements.txt

 # Copying the source code
COPY server_code/ .

# Exposing the port
EXPOSE 49152

 # Run the server code
 CMD ["python3", "cloud_server.py"]