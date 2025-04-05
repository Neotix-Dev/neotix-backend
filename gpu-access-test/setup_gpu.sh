#!/bin/bash

# Update package list
sudo apt-get update

# Install Linux headers
sudo apt-get install -y linux-headers-$(uname -r)

# Install NVIDIA driver
sudo apt-get install -y nvidia-driver-525

# Install CUDA dependencies
sudo apt-get install -y software-properties-common
sudo apt-get install -y python3-pip

# Install PyTorch with CUDA support
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Verify installation
nvidia-smi
python3 -c "import torch; print('CUDA available:', torch.cuda.is_available())"
