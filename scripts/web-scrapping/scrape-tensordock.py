import requests
import json
from datetime import datetime

# Base API URL
base_url = "https://dashboard.tensordock.com/api/session/deploy/hostnodes"

# Common parameters with relaxed constraints
params = {
    "minGPUCount": 1,
    "minRAM": 4,
    "minvCPUs": 2,
    "minStorage": 20,
    "minVRAM": 10
}

# Fetch data for both RTX and non-RTX GPUs
all_data = {}

# Non-RTX GPUs
params["requiresRTX"] = False
non_rtx_response = requests.get(base_url, params=params)
if non_rtx_response.status_code == 200:
    all_data["non_rtx"] = non_rtx_response.json()

# RTX GPUs
params["requiresRTX"] = True
rtx_response = requests.get(base_url, params=params)
if rtx_response.status_code == 200:
    all_data["rtx"] = rtx_response.json()

# Generate filename with today's date
today = datetime.now().strftime("%Y-%m-%d")
filename = f"tensordock{today}.json"

# Save the combined data to a JSON file
with open(filename, "w") as f:
    json.dump(all_data, f, indent=2)

print(f"Data saved to {filename}")