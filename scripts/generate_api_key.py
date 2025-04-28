#!/usr/bin/env python3
"""
Script to create a new API key via the backend's /v1/keys endpoint using the MASTER_API_KEY.
Usage:
  python generate_api_key.py <name> [permission]
Permissions: 'read' (default) or 'admin'
"""
import os
import sys
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def main():
    master_key = os.getenv("MASTER_API_KEY")
    if not master_key:
        print("Error: MASTER_API_KEY env var not set")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: generate_api_key.py <name> [permission]")
        sys.exit(1)

    name = sys.argv[1]
    permission = sys.argv[2] if len(sys.argv) > 2 else "read"

    api_url = os.getenv("NEOTIX_API_URL", "http://127.0.0.1:5000/api")
    endpoint = f"{api_url}/v1/keys"

    headers = {
        "X-API-Key": master_key,
        "Content-Type": "application/json"
    }

    payload = {"name": name}
    if permission in ["read", "admin"]:
        payload["permission"] = permission

    try:
        resp = requests.post(endpoint, headers=headers, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            print("Successfully created API key:")
            print(json.dumps(data, indent=2))
        else:
            print(f"Error {resp.status_code}: {resp.text}")
            sys.exit(1)
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
