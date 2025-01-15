from playwright.sync_api import sync_playwright
import json
from datetime import datetime

def scrape_scaleway_gpus():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Go to Scaleway's GPU instances page
        page.goto('https://www.scaleway.com/en/gpu-instances/')
        
        # Wait for the pricing table to load
        page.wait_for_selector('.Table_table__6cXug')
        
        # Get the pricing table content
        pricing_table = page.query_selector('.Table_table__6cXug')
        
        # Get all rows from the table
        rows = pricing_table.query_selector_all('tr')
        
        gpus_data = []
        # Skip header row by starting from index 1
        for row in rows[1:]:
            columns = row.query_selector_all('td')
            if len(columns) >= 2:  # Ensure we have at least name and price columns
                name = columns[0].inner_text().strip()
                gpu_memory = columns[1].inner_text().strip()
                peak_fp16_perf = columns[2].inner_text().strip()
                price = columns[-1].inner_text().strip()  # Usually last column is price
                
                gpus_data.append({
                    "name": name,
                    "gpu_memory": gpu_memory,
                    "peak_fp16_perf": peak_fp16_perf,
                    "hourly_price": price
                })
        
        browser.close()
        return gpus_data

if __name__ == "__main__":
    try:
        gpu_data = scrape_scaleway_gpus()
        
        # Format today's date as YYYYMMDD
        today = datetime.now().strftime("%Y%m%d")
        
        # Save to file
        with open(f'scaleway{today}.json', 'w') as f:
            json.dump(gpu_data, indent=2, fp=f)
            
        print(f"Data saved to scaleway{today}.json")
    except Exception as e:
        print(f"Error occurred: {e}")