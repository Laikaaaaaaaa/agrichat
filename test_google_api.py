"""
Test Google Custom Search API đơn giản
"""
import os
import requests
from dotenv import load_dotenv

def test_google_custom_search():
    print("🔍 Testing Google Custom Search API...")
    load_dotenv()
    
    # API configuration
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")

    if not api_key or not cse_id:
        print("⚠️  GOOGLE_API_KEY hoặc GOOGLE_CSE_ID chưa được cấu hình trong .env")
        return
    
    # Test query
    query = "tomato agriculture"
    
    try:
        # API endpoint
        base_url = "https://www.googleapis.com/customsearch/v1"
        
        params = {
            'key': api_key,
            'cx': cse_id,
            'q': query,
            'searchType': 'image',
            'num': 4,
            'imgSize': 'medium',
            'imgType': 'photo',
            'safe': 'active'
        }
        
        print(f"📡 Making request to: {base_url}")
        print(f"🔍 Query: {query}")
        
        response = requests.get(base_url, params=params, timeout=15)
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            print(f"✅ SUCCESS: Found {len(items)} images")
            
            for i, item in enumerate(items, 1):
                print(f"  {i}. {item.get('title', 'No title')}")
                print(f"     URL: {item.get('link', 'No URL')}")
                print(f"     Source: {item.get('displayLink', 'Unknown')}")
                print()
                
        elif response.status_code == 403:
            print("❌ Error 403: API key issues or quota exceeded")
            print("Response:", response.text)
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_google_custom_search()