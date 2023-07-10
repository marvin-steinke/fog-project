# Creating base image
FROM python:3.10.6

# Setting up the working directory
WORKDIR /fog-app

# Install dependencies
COPY requirements.txt .
RUN apt-install python3-pip
RUN pip install -r requirements.txt

# Copying the source code
COPY . /fog-app

# Exposing the ports
EXPOSE 63270    
EXPOSE 63271
EXPOSE 63272
EXPOSE 5006

# Specify the command to execute the server script
CMD ["python3", "cloud_server.py"]
