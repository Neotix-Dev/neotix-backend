#!/bin/bash

# Set proper permissions for the key file
chmod 400 cluster_key.pem

# Copy the test script to the remote server
# scp -i cluster_key.pem test_gpu.py ubuntu@44.222.142.221:~/test_gpu.py

# Connect to the remote server and run the test
ssh -i cluster_key.pem ubuntu@44.222.142.221 #"python3 test_gpu.py"
