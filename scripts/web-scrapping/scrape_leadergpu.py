import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def scrape_leadergpu():
    url = "https://www.leadergpu.com/filter_servers?filterExpression=os%3Awindows_server%3Bavailable_server%3Bavailable_server_next3d%3Bmonth%3A1"
    # Get JSON response and extract HTML from it
    response = requests.get(url).json()
    html_content = response['matchesHtml']
    soup = BeautifulSoup(html_content, 'html.parser')
    
    gpu_sections = soup.find_all('section', class_='b-product-gpu')
    servers = []
    
    for section in gpu_sections:
        # Basic info from title
        title_div = section.find('div', class_='b-product-gpu-title')
        if not title_div:
            continue
        print(title_div)
            
        # Extract server ID and title
        link = title_div.find('a')
        title = link.text.strip() if link else None
        server_id = link['href'].split('/')[-1] if link else None
        
        # Extract pricing from data-sort
        sort_data = title_div.get('data-sort', '').split(';')
        monthly_price = float(sort_data[1]) if len(sort_data) > 1 else None
        
        # Extract GPU configuration
        config_div = section.find('div', class_='config-list')
        gpu_info = config_div.find('div', string=lambda text: text and 'GPU:' in text) if config_div else None
        gpu_specs = gpu_info.find_next('p').text.strip() if gpu_info else None
        
        # Extract RAM, CPU, and GPU RAM
        gpu_ram = None
        cpu = None
        ram = None
        nvme = None
        network = None
        
        if config_div:
            for div in config_div.find_all('div', class_='mb-10'):
                text = div.text.strip()
                if 'GPU RAM:' in text:
                    gpu_ram = div.find('span', class_=None).text.strip()
                elif 'CPU:' in text:
                    cpu = div.find('span', class_=None).text.strip()
                elif 'RAM:' in text:
                    ram = div.find('span', class_=None).text.strip()
                elif 'NVME:' in text:
                    nvme = div.find('span', class_=None).text.strip()
                elif 'Internal network:' in text:
                    network = div.find('span', class_=None).text.strip()
        
        # Extract prices
        prices_div = section.find('div', class_='b-product-gpu-prices')
        price_items = {}
        if prices_div:
            for li in prices_div.find_all('li', class_='d-flex'):
                price_text = li.find('p').text.strip()
                if 'month' in price_text:
                    price_items['monthly'] = price_text
                elif 'week' in price_text:
                    price_items['weekly'] = price_text
                elif 'day' in price_text:
                    price_items['daily'] = price_text
                elif 'minute' in price_text:
                    price_items['per_minute'] = price_text
        
        server_info = {
            'server_id': server_id,
            'title': title,
            'monthly_price_eur': monthly_price,
            'detailed_prices': price_items,
            'specifications': {
                'gpu_info': gpu_specs,
                'gpu_ram': gpu_ram,
                'cpu': cpu,
                'ram': ram,
                'nvme': nvme,
                'network': network
            },
            'configuration_url': f"https://www.leadergpu.com/server_configurations/{server_id}"
        }
        
        servers.append(server_info)
    
    return servers

if __name__ == "__main__":
    try:
        servers = scrape_leadergpu()
        
        # Generate filename with today's date
        today = datetime.now().strftime('%Y%m%d')
        filename = f'leadergpu_{today}.json'
        
        # Save to JSON file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(servers, f, indent=2, ensure_ascii=False)
            
        print(f"Data saved to {filename}")
        print(f"Found {len(servers)} server configurations")
    except Exception as e:
        print(f"Error occurred: {e}")
