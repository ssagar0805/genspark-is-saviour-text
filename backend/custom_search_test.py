import requests 
import os 
from dotenv import load_dotenv 
 
load_dotenv() 
api_key = os.getenv('CUSTOM_SEARCH_API_KEY') 
engine_id = os.getenv('CUSTOM_SEARCH_ENGINE_ID') 
 
print(f'Testing Custom Search API...') 
print(f'API Key: {api_key[:15] if api_key else None}...') 
print(f'Engine ID: {engine_id}') 
 
print(f'URL: {url[:80]}...') 
 
try: 
    response = requests.get(url, timeout=10) 
    print(f'Status Code: {response.status_code}') 
    if response.status_code != 200: 
        print(f'Error Response: {response.text[:500]}') 
    else: 
        data = response.json() 
        total_results = data.get('searchInformation', {}).get('totalResults', '0') 
        print(f'Total Results: {total_results}') 
        items = data.get('items', []) 
        print(f'Items Found: {len(items)}') 
        if items: 
            print(f'First Result: {items[0].get("title", "No title")}') 
except Exception as e: 
    print(f'Request Error: {str(e)}') 
