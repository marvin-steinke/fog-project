#!/bin/bash

# Variables
USE_INTERNAL_IP=false  # Set to true if you want to use the internal IP address
INSTANCE_IP_EXTERNAL="34.141.104.207"
INSTANCE_IP_INTERNAL="INTERNAL_IP_ADDRESS"
INSTANCE_USER="niklasfo"

# Determine IP address to use
if [ "$USE_INTERNAL_IP" = true ]; then
  INSTANCE_IP=$INSTANCE_IP_INTERNAL
else
  INSTANCE_IP=$INSTANCE_IP_EXTERNAL
fi

# Create directory on remote instance
ssh -i ~/.ssh/your_private_key.pem $INSTANCE_USER@$INSTANCE_IP "sudo mkdir -p /local/cloud_node"

# Copy files to remote instance
scp -i ~/.ssh/your_private_key.pem ./app $INSTANCE_USER@$INSTANCE_IP:/local/cloud_node
scp -i ~/.ssh/your_private_key.pem ./Dockerfile $INSTANCE_USER@$INSTANCE_IP:/local/cloud_node
scp -i ~/.ssh/your_private_key.pem ./docker-compose.yaml $INSTANCE_USER@$INSTANCE_IP:/local/cloud_node
scp -i ~/.ssh/your_private_key.pem ./requirements.txt $INSTANCE_USER@$INSTANCE_IP:/local/cloud_node

# SSH into remote instance
ssh -i ~/.ssh/your_private_key.pem $INSTANCE_USER@$INSTANCE_IP
