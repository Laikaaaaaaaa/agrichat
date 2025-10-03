"""
Google Images API Search Engine
Sử dụng Google Custom Search API để tìm ảnh chất lượng cao
"""
import os
import requests
import time
import random
import logging
from dotenv import load_dotenv

class GoogleImagesAPI:
    def __init__(self):
        load_dotenv()

        # Google Custom Search API credentials
        self.api_key = os.getenv("GOOGLE_API_KEY", "").strip() or None
        # Cho phép override riêng cho Google Images nếu cần
        self.search_engine_id = (
            os.getenv("GOOGLE_IMAGE_CSE_ID", "").strip()
            or os.getenv("GOOGLE_CSE_ID", "").strip()
            or None
        )
        self.base_url = "https://www.googleapis.com/customsearch/v1"

        if not self.api_key or not self.search_engine_id:
            logging.warning(
                "⚠️  GOOGLE_API_KEY hoặc GOOGLE_IMAGE_CSE_ID/GOOGLE_CSE_ID chưa được cấu hình. Google Images API sẽ không hoạt động."
            )
        
        # Vietnamese to English translation for better search results
        self.translation_map = {
            'xoài': 'mango fruit',
            'cà chua': 'tomato',
            'lúa': 'rice plant',
            'ngô': 'corn maize',
            'mía': 'sugarcane',
            'lúa mì': 'wheat',
            'táo': 'apple fruit',
            'cà rót': 'eggplant',
            'khoai tây': 'potato',
            'khoai lang': 'sweet potato',
            'cà rốt': 'carrot',
            'bắp cải': 'cabbage',
            'rau muống': 'water spinach',
            'dưa chuột': 'cucumber',
            'ớt': 'chili pepper',
            'hành tây': 'onion',
            'tỏi': 'garlic',
            'cam': 'orange fruit',
            'chanh': 'lemon',
            'chuối': 'banana',
            'dừa': 'coconut',
            'đu đủ': 'papaya',
            'nho': 'grape',
            'dâu tây': 'strawberry',
            'gà': 'chicken poultry',
            'bò': 'cattle cow',
            'heo': 'pig swine',
            'cừu': 'sheep',
            'dê': 'goat',
            'vịt': 'duck',
            'cá': 'fish aquaculture',
            'tôm': 'shrimp',
            'máy kéo': 'tractor farm',
            'máy gặt': 'harvester',
            'máy cày': 'plow',
            'hoa hướng dương': 'sunflower',
            'hoa hồng': 'rose flower',
            'hoa sen': 'lotus flower',
            'đất': 'agricultural soil',
            'phân bón': 'fertilizer',
            'nước tưới': 'irrigation',
            'nhà kính': 'greenhouse',
            'hạt giống': 'seeds',
            'cây giống': 'seedlings',
            'sâu hại': 'crop pests',
            'thuốc trừ sâu': 'pesticide',
            'bệnh cây trồng': 'plant disease',
            'nông nghiệp': 'agriculture farming'
        }
    
    def search_images(self, query, max_results=4):
        """
        Tìm ảnh từ Google Images với quality check
        """
        print(f"🔍 Google Images search for: {query}")
        
        # Translate Vietnamese to English for better results
        english_query = self.translate_query(query)
        print(f"🌐 Translated query: {english_query}")
        
        images = []
        
        try:
            # Search with main query
            results = self._search_google(english_query, max_results)
            images.extend(results)
            
            # If not enough results, try with additional terms
            if len(images) < max_results:
                additional_query = f"{english_query} agriculture farming"
                additional_results = self._search_google(additional_query, max_results - len(images))
                images.extend(additional_results)
            
            # Filter and validate images
            valid_images = []
            for img in images:
                if self.validate_image_url(img['url']):
                    valid_images.append(img)
                    if len(valid_images) >= max_results:
                        break
            
            print(f"✅ Found {len(valid_images)} valid images")
            return valid_images
            
        except Exception as e:
            print(f"❌ Google Images API error: {e}")
            return self.create_fallback_images(query, max_results)
    
    def translate_query(self, query):
        """Dịch từ tiếng Việt sang tiếng Anh"""
        query_lower = query.lower().strip()
        
        # Exact match first
        if query_lower in self.translation_map:
            return self.translation_map[query_lower]
        
        # Partial match
        for vn_term, en_term in self.translation_map.items():
            if vn_term in query_lower:
                return en_term
        
        # If no translation found, return original + agriculture
        return f"{query} agriculture"
    
    def _search_google(self, query, num_results):
        """Gọi Google Custom Search API"""
        if not self.api_key or not self.search_engine_id:
            logging.warning("⚠️  Thiếu GOOGLE_API_KEY hoặc GOOGLE_IMAGE_CSE_ID/GOOGLE_CSE_ID. Bỏ qua Google Custom Search.")
            return []

        params = {
            'key': self.api_key,
            'cx': self.search_engine_id,
            'q': query,
            'searchType': 'image',
            'num': min(num_results, 10),  # Google API max 10 per request
            'safe': 'active',
            'imgSize': 'medium',
            'imgType': 'photo',
            'rights': 'cc_publicdomain,cc_attribute,cc_sharealike,cc_noncommercial'
        }
        
        response = requests.get(self.base_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        images = []
        
        if 'items' in data:
            for i, item in enumerate(data['items']):
                img_data = {
                    'url': item['link'],
                    'title': item.get('title', f'Google Image {i+1}'),
                    'description': item.get('snippet', 'High quality image from Google'),
                    'photographer': item.get('displayLink', 'Google Images'),
                    'source': 'google_images'
                }
                images.append(img_data)
        
        return images
    
    def validate_image_url(self, url):
        """Kiểm tra URL ảnh có hợp lệ không"""
        try:
            # Quick HEAD request to check if URL is accessible
            response = requests.head(url, timeout=5, allow_redirects=True)
            
            # Check if response is successful and content is image
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                if any(img_type in content_type for img_type in ['image/', 'jpeg', 'jpg', 'png', 'gif', 'webp']):
                    return True
            
            print(f"❌ Invalid image URL: {url} (status: {response.status_code})")
            return False
            
        except Exception as e:
            print(f"❌ URL validation error for {url}: {e}")
            return False
    
    def create_fallback_images(self, query, count):
        """Tạo ảnh fallback chất lượng cao khi API thất bại"""
        print(f"🔄 Creating {count} fallback images for: {query}")
        
        fallback_images = []
        colors = ['4CAF50', 'FF9800', '2196F3', 'E91E63', '9C27B0', 'FF5722']
        
        for i in range(count):
            color = colors[i % len(colors)]
            fallback_url = f"https://via.placeholder.com/400x300/{color}/FFFFFF?text={query.replace(' ', '+')}+{i+1}"
            
            fallback_images.append({
                'url': fallback_url,
                'title': f'{query.title()} - Ảnh {i+1}',
                'description': f'Ảnh minh họa chất lượng cao cho {query}',
                'photographer': 'AgriSense AI',
                'source': 'fallback'
            })
        
        return fallback_images

# Test function
def test_google_images():
    """Test Google Images API"""
    print("🚀 TEST GOOGLE IMAGES API")
    print("=" * 50)
    
    api = GoogleImagesAPI()
    
    test_queries = ['xoài', 'cà chua', 'lúa', 'nông nghiệp']
    
    for query in test_queries:
        print(f"\n🔍 Testing: {query}")
        print("-" * 30)
        
        images = api.search_images(query, 2)
        
        for i, img in enumerate(images):
            print(f"📸 {i+1}. {img['title']}")
            print(f"   URL: {img['url'][:60]}...")
            print(f"   Source: {img['source']}")

if __name__ == "__main__":
    test_google_images()