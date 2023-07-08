#!/bin/bash

# Google Cloud instance details
GCP_USER="niklasfo"
GCP_IP="34.141.104.207"
GCP_PATH="~/cloud_server"  

# Path to local directory to be copied
LOCAL_DIRECTORY=$(pwd)

# SCP command to copy the directory
scp -r $LOCAL_DIRECTORY $GCP_USER@$GCP_IP:$GCP_PATH
