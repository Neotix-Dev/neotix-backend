#!/bin/bash

API_URL="http://localhost:5000/api"

# Add GPU listings
echo "Adding GPU listings..."

curl -X POST "${API_URL}/gpu/add_gpu" \
     -H "Content-Type: application/json" \
     -d '{
        "name": "NVIDIA GeForce RTX 3080",
        "current_price": 699.99,
        "price_metric": "USD",
        "price_change": "-5%",
        "reliability": 4.5,
        "flops": 29700,
        "vram": 10,
        "description": "High-end GPU for gaming and content creation",
        "image_url": "https://example.com/rtx3080.jpg",
        "host_id": 1
     }'
echo

curl -X POST "${API_URL}/gpu/add_gpu" \
     -H "Content-Type: application/json" \
     -d '{
        "name": "AMD Radeon RX 6800 XT",
        "current_price": 649.99,
        "price_metric": "USD",
        "price_change": "+2%",
        "reliability": 4.3,
        "flops": 20600,
        "vram": 16,
        "description": "Powerful GPU for high-performance gaming",
        "image_url": "https://example.com/rx6800xt.jpg",
        "host_id": 2
     }'
echo

curl -X POST "${API_URL}/gpu/add_gpu" \
     -H "Content-Type: application/json" \
     -d '{
        "name": "NVIDIA GeForce RTX 3070",
        "current_price": 499.99,
        "price_metric": "USD",
        "price_change": "0%",
        "reliability": 4.4,
        "flops": 20400,
        "vram": 8,
        "description": "Excellent performance for 1440p gaming",
        "image_url": "https://example.com/rtx3070.jpg",
        "host_id": 3
     }'
echo

curl -X POST "${API_URL}/gpu/add_gpu" \
     -H "Content-Type: application/json" \
     -d '{
        "name": "AMD Radeon RX 6700 XT",
        "current_price": 479.99,
        "price_metric": "USD",
        "price_change": "-3%",
        "reliability": 4.2,
        "flops": 13210,
        "vram": 12,
        "description": "Great for 1440p gaming with high frame rates",
        "image_url": "https://example.com/rx6700xt.jpg",
        "host_id": 4
     }'
echo

curl -X POST "${API_URL}/gpu/add_gpu" \
     -H "Content-Type: application/json" \
     -d '{
        "name": "NVIDIA GeForce RTX 3060 Ti",
        "current_price": 399.99,
        "price_metric": "USD",
        "price_change": "+1%",
        "reliability": 4.3,
        "flops": 16200,
        "vram": 8,
        "description": "Excellent value for 1080p and 1440p gaming",
        "image_url": "https://example.com/rtx3060ti.jpg",
        "host_id": 2
     }'
echo

curl -X POST "${API_URL}/gpu/add_gpu" \
     -H "Content-Type: application/json" \
     -d '{
        "name": "AMD Radeon RX 6600 XT",
        "current_price": 379.99,
        "price_metric": "USD",
        "price_change": "-2%",
        "reliability": 4.1,
        "flops": 10600,
        "vram": 8,
        "description": "Solid performer for 1080p gaming",
        "image_url": "https://example.com/rx6600xt.jpg",
        "host_id": 4
     }'
echo

curl -X POST "${API_URL}/gpu/add_gpu" \
     -H "Content-Type: application/json" \
     -d '{
        "name": "NVIDIA GeForce RTX 3090",
        "current_price": 1499.99,
        "price_metric": "USD",
        "price_change": "-10%",
        "reliability": 4.7,
        "flops": 35580,
        "vram": 24,
        "description": "Ultimate GPU for 4K gaming and professional work",
        "image_url": "https://example.com/rtx3090.jpg",
        "host_id": 1
     }'
echo

curl -X POST "${API_URL}/gpu/add_gpu" \
     -H "Content-Type: application/json" \
     -d '{
        "name": "AMD Radeon RX 6900 XT",
        "current_price": 999.99,
        "price_metric": "USD",
        "price_change": "-5%",
        "reliability": 4.6,
        "flops": 23040,
        "vram": 16,
        "description": "AMDs flagship GPU for enthusiast gamers",
        "image_url": "https://example.com/rx6900xt.jpg",
        "host_id": 2
     }'
echo

echo "GPU listings added successfully."
