import json
import os
from datetime import datetime
from typing import Dict, Any
import re

def extract_vram_from_name(name: str) -> int:
    """Extract VRAM from GPU name if possible."""
    vram_pattern = r'(\d+)GB'
    match = re.search(vram_pattern, name, re.IGNORECASE)
    return int(match.group(1)) if match else None

def round_price(price: float) -> float:
    """Round price to 2 decimal places."""
    return round(price, 2) if price is not None else None

def round_flops(flops: float) -> float:
    """Round FLOPS to 2 decimal places."""
    return round(flops, 2) if flops is not None else None

def round_reliability(reliability: float) -> float:
    """Round reliability to 1 decimal place."""
    return round(reliability, 1) if reliability is not None else None

def normalize_latitude_data(data: Dict[str, Any]) -> list:
    normalized = []
    for plan_type in ['container_plans', 'regular_plans']:
        for plan in data.get(plan_type, []):
            specs = plan['specs']
            normalized.append({
                "id": f"latitude_{plan['slug']}",
                "name": plan['name'],
                "provider": "Latitude",
                "pricing": {
                    "amount": round_price(float(specs.get('price', 0))),
                    "currency": "USD",
                    "unit": "hour",
                    "price_change": None
                },
                "specifications": {
                    "vram": extract_vram_from_name(plan['name']),
                    "number_of_gpus": specs.get('gpu_count', 1),
                    "flops": None,
                    "reliability": None
                },
                "region": ", ".join(plan['regions']),
                "available": True,
                "timestamp": datetime.now().isoformat()
            })
    return normalized

def normalize_tensordock_data(data: Dict[str, Any]) -> list:
    normalized = []
    for gpu_type in ['rtx', 'non_rtx']:
        # Check if the item is a dictionary, if not, skip it
        gpu_list = data.get(gpu_type, [])
        if not isinstance(gpu_list, list):
            continue
            
        for item in gpu_list:
            if not isinstance(item, dict):
                continue
                
            normalized.append({
                "id": f"tensordock_{item.get('id', '')}",
                "name": item.get('gpu_name', ''),
                "provider": "TensorDock",
                "pricing": {
                    "amount": round_price(float(item.get('price', 0))),
                    "currency": "USD",
                    "unit": "hour",
                    "price_change": None
                },
                "specifications": {
                    "vram": extract_vram_from_name(item.get('gpu_name', '')),
                    "number_of_gpus": item.get('gpu_count', 1),
                    "flops": None,
                    "reliability": None
                },
                "region": item.get('region', 'Unknown'),
                "available": True,
                "timestamp": datetime.now().isoformat()
            })
    return normalized

def normalize_vastai_data(data: Dict[str, Any]) -> list:
    normalized = []
    
    # GPU name mapping for standardization
    gpu_name_mapping = {
        "RTX 6000Ada": "RTX 6000Ada",
        "RTX A6000": "RTX A6000",
        "A6000": "RTX A6000",
        "RTX 3090": "RTX 3090",
        "RTX 3080": "RTX 3080",
        "RTX 3070": "RTX 3070",
        "RTX 4090": "RTX 4090",
        "RTX 4080": "RTX 4080",
        "A100": "A100",
        "H100": "H100",
        "A40": "A40",
        "L40": "L40",
        "V100": "V100",
        "T4": "T4"
    }
    
    def standardize_gpu_name(name: str) -> str:
        if not name:
            return "Unknown GPU"
        
        # Remove extra spaces and standardize spacing
        name = name.strip()
        name = re.sub(r'\s+', ' ', name)
        
        # Remove manufacturer prefix if present
        for manufacturer in ["NVIDIA", "AMD", "Intel"]:
            name = name.replace(f"{manufacturer} ", "")
        
        # First try exact match
        standardized = gpu_name_mapping.get(name)
        if standardized:
            return standardized
        
        # Try without spaces
        no_spaces = name.replace(' ', '')
        for key, value in gpu_name_mapping.items():
            if no_spaces.lower() == key.replace(' ', '').lower():
                return value
        
        # Try partial matches
        for key, value in gpu_name_mapping.items():
            if key.lower() in name.lower() or name.lower() in key.lower():
                if len(key) > 3:  # Avoid matching very short strings
                    return value
        
        return name
    
    for _, gpu in data.items():
        # Convert VRAM from MB to GB and round to nearest integer
        vram_mb = gpu.get('gpu_ram', None)
        vram_gb = round(vram_mb / 1024) if vram_mb is not None else None
        
        # Standardize GPU name
        gpu_name = standardize_gpu_name(gpu.get('gpu_name', ''))
        
        normalized.append({
            "id": f"vastai_{gpu.get('id', '')}",
            "name": gpu_name,
            "provider": "Vast.ai",
            "pricing": {
                "amount": round(float(gpu.get('dph_total', 0)), 2),
                "currency": "USD",
                "unit": "hour",
                "price_change": None
            },
            "specifications": {
                "vram": vram_gb,
                "number_of_gpus": gpu.get('num_gpus', 1),
                "flops": gpu.get('total_flops', None),
                "reliability": gpu.get('reliability2', None) * 100 if gpu.get('reliability2') else None
            },
            "region": gpu.get('location', 'Unknown'),
            "available": gpu.get('rentable', False),
            "timestamp": datetime.now().isoformat()
        })
    return normalized

def normalize_scaleway_data(data, timestamp):
    normalized = []
    for item in data:
        gpu_name = item["name"].replace("NVIDIA ", "")
        # Remove any "Nx" prefix and "GPU" suffix
        gpu_name = re.sub(r'^\d+x\s*', '', gpu_name)
        gpu_name = re.sub(r'\s*GPU$', '', gpu_name)
        # Remove "Tensor Core" suffix
        gpu_name = re.sub(r'\s*Tensor Core$', '', gpu_name)
        
        # Extract VRAM size
        vram = int(item["gpu_memory"].replace("GB", ""))
        
        # Extract FLOPS
        flops = float(item["peak_fp16_perf"].replace(",", "").replace(" TFLOPS", ""))
        
        # Extract price
        price = float(item["hourly_price"].replace("€", "").replace("/HOUR", ""))
        
        # Try to extract number of GPUs from name, default to 1 if not found
        num_gpus_match = re.match(r'(\d+)x', item["name"])
        num_gpus = int(num_gpus_match.group(1)) if num_gpus_match else 1
        
        normalized.append({
            "id": f"scaleway_{gpu_name.lower().replace(' ', '_')}",
            "name": gpu_name,
            "provider": "Scaleway",
            "pricing": {
                "amount": price,
                "currency": "EUR",
                "unit": "hour",
                "price_change": None
            },
            "specifications": {
                "vram": vram,
                "number_of_gpus": num_gpus,
                "flops": flops,
                "reliability": None
            },
            "region": "Europe",
            "available": True,
            "timestamp": timestamp
        })
    return normalized

def normalize_leadergpu_data(data, timestamp):
    normalized = []
    
    # Enhanced GPU name mapping to standardize names
    gpu_name_mapping = {
        "H100": "H100",
        "3090": "RTX 3090",
        "3080": "RTX 3080",
        "3070": "RTX 3070",
        "A6000": "RTX A6000",
        "A6000 Ada": "RTX 6000Ada",
        "L40S": "L40S",
        "L40": "L40",
        "L20": "L20",
        "4090": "RTX 4090",
        "4080": "RTX 4080",
        "A100": "A100",
        "A10": "A10",
        "1080Ti": "GTX 1080 Ti",
        "1080": "GTX 1080",
        "RTX 6000 Ada": "RTX 6000 Ada",
        "RTX 6000": "RTX 6000",
        "V100": "V100",
        "T4": "T4"
    }
    
    # Memory type mapping
    memory_type_mapping = {
        "GDDR6X": "GDDR6X",
        "GDDR6": "GDDR6",
        "HBM2": "HBM2",
        "HBM2e": "HBM2e",
        "HBM3": "HBM3",
        "GDDR5x": "GDDR5x"
    }
    
    def extract_gpu_info(title):
        # Enhanced pattern matching for various formats
        # Matches: "8xA6000", "8 x A6000", "1 x RTX 6000 Ada", "4×A100"
        gpu_pattern = r'^(\d+)\s*[x×]\s*([^,]+)'
        match = re.match(gpu_pattern, title, re.IGNORECASE)
        
        if match:
            num_gpus = int(match.group(1))
            gpu_model = match.group(2).strip()
        else:
            # If no multiplier found, assume 1 GPU and try to extract model
            num_gpus = 1
            gpu_model = title.split(',')[0].strip()
        
        return num_gpus, gpu_model
    
    def calculate_hourly_rate(monthly_price):
        try:
            return round(float(monthly_price) / 730.484, 2)
        except (ValueError, TypeError):
            print(f"Error calculating hourly rate for price: {monthly_price}")
            return None
    
    def extract_vram_info(vram_info):
        if not vram_info:
            return None, None
            
        vram = None
        memory_type = None
        
        # Match total VRAM and memory type
        # Patterns: "160GB (2x80GB)", "48GB GDDR6X", "384GB (8x48GB) HBM2"
        vram_pattern = r'(\d+)\s*GB'
        mem_type_pattern = r'(GDDR6X|GDDR6|HBM2e|HBM2|HBM3)'
        
        vram_match = re.search(vram_pattern, vram_info)
        mem_type_match = re.search(mem_type_pattern, vram_info, re.IGNORECASE)
        
        if vram_match:
            vram = int(vram_match.group(1))
        
        if mem_type_match:
            memory_type = memory_type_mapping.get(mem_type_match.group(1).upper())
        
        return vram, memory_type
    
    def standardize_region(region_info):
        region_mapping = {
            "eu": "Europe",
            "europe": "Europe",
            "us": "United States",
            "usa": "United States",
            "asia": "Asia"
        }
        if not region_info:
            return "Europe"  # Default region for LeaderGPU
            
        region_key = region_info.lower().strip()
        return region_mapping.get(region_key, region_info)
    
    for item in data:
        try:
            num_gpus, gpu_model = extract_gpu_info(item["title"])
            
            # Get standardized GPU name
            standardized_name = None
            for key, value in gpu_name_mapping.items():
                if key.lower() in gpu_model.lower():
                    standardized_name = value
                    break
            
            if not standardized_name:
                standardized_name = gpu_model
            
            vram, memory_type = extract_vram_info(item["specifications"].get("gpu_ram"))
            region = standardize_region(item.get("region"))
            
            normalized.append({
                "id": f"leadergpu_{item['server_id']}",
                "name": standardized_name,
                "provider": "LeaderGPU",
                "pricing": {
                    "amount": calculate_hourly_rate(item["monthly_price_eur"]),
                    "currency": "EUR",
                    "unit": "hour",
                    "price_change": None
                },
                "specifications": {
                    "vram": vram,
                    "memory_type": memory_type,
                    "number_of_gpus": num_gpus,
                    "flops": None,
                    "reliability": None
                },
                "region": region,
                "available": True,
                "timestamp": timestamp
            })
            
        except Exception as e:
            print(f"Error processing server {item.get('server_id', 'unknown')}: {str(e)}")
            continue
    
    return normalized

def process_directory():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    today = datetime.now().strftime('%Y%m%d')
    
    # Create normalized directory if it doesn't exist
    normalized_dir = os.path.join(script_dir, 'normalized')
    os.makedirs(normalized_dir, exist_ok=True)
    
    normalizers = {
        'latitude': normalize_latitude_data,
        'tensordock': normalize_tensordock_data,
        'vastai': normalize_vastai_data,
        'scaleway': lambda data: normalize_scaleway_data(data, datetime.now().isoformat()),
        'leadergpu': lambda data: normalize_leadergpu_data(data, datetime.now().isoformat()),
    }
    
    all_normalized_data = []
    
    # Process each JSON file
    for filename in os.listdir(script_dir):
        if filename.endswith('.json'):
            for provider in normalizers.keys():
                if provider in filename.lower():
                    with open(os.path.join(script_dir, filename), 'r') as f:
                        data = json.load(f)
                        normalized = normalizers[provider](data)
                        all_normalized_data.extend(normalized)
    
    # Save combined normalized data
    output_file = os.path.join(normalized_dir, f'normalized_gpu_data_{today}.json')
    with open(output_file, 'w') as f:
        json.dump(all_normalized_data, f, indent=2)
    
    print(f"Normalized data saved to: {output_file}")

if __name__ == "__main__":
    process_directory()
