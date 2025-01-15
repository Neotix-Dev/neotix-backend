import requests
import json
from datetime import datetime

def scrape_vastai():
    # API URL
    url = "https://cloud.vast.ai/api/v0/bundles/"
    
    # Query parameters
    params = {
        "q": {
            "disk_space": {"gte": 13.454342644059432},
            "reliability2": {"gte": 0.9927008691532114},
            "duration": {"gte": 6294.080870000899},
            "verified": {"eq": True},
            "rentable": {"eq": True},
            "dph_total": {"lte": 128},
            "inet_up_cost": {"lte": 0.09753068502171296},
            "inet_down_cost": {"lte": 0.09753068502171296},
            "gpu_mem_bw": {"gte": 9.999999999999996, "lte": 8034.141162462954},
            "sort_option": {
                "0": ["dph_total", "asc"],
                "1": ["total_flops", "asc"]
            },
            "order": [["dph_total", "asc"], ["total_flops", "asc"]],
            "num_gpus": {"gte": 0, "lte": 18},
            "allocated_storage": 13.454342644059432,
            "cuda_max_good": {"gte": "12.1"},
            "compute_cap": {"gte": 500},
            "has_avx": {"eq": True},
            "limit": 1000,
            "extra_ids": [],
            "type": "ask",
            "direct_port_count": {"gte": 2}
        }
    }

    try:
        # Make the request
        response = requests.get(url, params={"q": json.dumps(params["q"])})
        response.raise_for_status()
        
        # Parse the response and extract just the offers
        data = response.json()
        gpu_data = {str(i): gpu for i, gpu in enumerate(data.get("offers", []))}
        
        # Generate filename with today's date
        today = datetime.now().strftime("%Y%m%d")
        filename = f"VastAI{today}.json"
        
        # Save to file
        with open(filename, 'w') as f:
            json.dump(gpu_data, f, indent=2)
            
        print(f"Data successfully saved to {filename}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
    except IOError as e:
        print(f"Error writing to file: {e}")

if __name__ == "__main__":
    scrape_vastai()
