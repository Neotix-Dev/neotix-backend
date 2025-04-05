import torch
import subprocess
import sys

def check_gpu():
    print("PyTorch version:", torch.__version__)
    print("\nGPU Information:")
    print("CUDA available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("CUDA version:", torch.version.cuda)
        print("GPU device name:", torch.cuda.get_device_name(0))
        print("Number of GPUs:", torch.cuda.device_count())

def main():
    print("Testing GPU access on remote server...")
    check_gpu()
    
if __name__ == "__main__":
    main()
