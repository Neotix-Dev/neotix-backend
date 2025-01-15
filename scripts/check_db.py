import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models.gpu_listing import Host, GPUListing
from utils.database import db

def check_db():
    app = create_app()
    with app.app_context():
        # Check hosts
        hosts = Host.query.all()
        print(f"\nFound {len(hosts)} hosts:")
        for host in hosts:
            print(f"- {host.name}")
            
        # Check GPU listings
        gpus = GPUListing.query.all()
        print(f"\nFound {len(gpus)} GPU listings:")
        for i, gpu in enumerate(gpus[:5], 1):
            print(f"\n{i}. GPU Details:")
            print(f"   - Name: {gpu.name}")
            print(f"   - Price: ${gpu.current_price}/{gpu.price_metric}")
            print(f"   - VRAM: {gpu.vram}GB")
            print(f"   - Provider: {gpu.host.name}")
            print(f"   - Reliability: {gpu.reliability}")
            print(f"   - FLOPS: {gpu.flops}")
            
        if len(gpus) > 5:
            print(f"\n... and {len(gpus) - 5} more GPUs")

if __name__ == "__main__":
    check_db()
