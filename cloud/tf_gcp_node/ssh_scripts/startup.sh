#!/bin/bash

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker $USER

# Install Docker Compose
apt-get install -y docker-compose

# Clone your repository
git clone <your_repository_url>

# Navigate to the repository directory
cd <your_repository_directory>

# Start the cloud server using Docker Compose
docker-compose up -d
