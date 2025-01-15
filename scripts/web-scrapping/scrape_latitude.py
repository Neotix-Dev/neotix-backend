import requests
import json
from datetime import datetime

def scrape_latitude_pricing():
    # Fetch JSON data from the API endpoint
    url = 'https://www.latitude.sh/_next/data/website-dcdab91bc4bee7f501bc6df274ac26addd7e0d02/en/network/pricing.json'
    response = requests.get(url)
    data = response.json()
    
    # Extract both container plans and regular plans data
    container_plans = data['pageProps']['containersPlansData']
    regular_plans = data['pageProps']['plansData']
    
    # Process and structure the data
    pricing_data = {
        'container_plans': [],
        'regular_plans': []
    }
    
    # Process container plans
    for plan in container_plans:
        plan_info = {
            'name': plan['attributes']['name'],
            'slug': plan['attributes']['slug'],
            'specs': plan['attributes']['specs'],
            'regions': plan['attributes']['regions']
        }
        pricing_data['container_plans'].append(plan_info)
    
    # Process regular plans
    for plan in regular_plans:
        plan_info = {
            'name': plan['attributes']['name'],
            'slug': plan['attributes']['slug'],
            'specs': plan['attributes']['specs'],
            'regions': plan['attributes']['regions']
        }
        pricing_data['regular_plans'].append(plan_info)
    
    return pricing_data

def save_to_json(pricing_data):
    # Format the date as YYYYMMDD
    today = datetime.now().strftime('%Y%m%d')
    
    # Save to JSON file
    with open(f'latitude{today}.json', 'w') as f:
        json.dump(pricing_data, f, indent=4)

if __name__ == "__main__":
    pricing_data = scrape_latitude_pricing()
    save_to_json(pricing_data)
