"""
wikimedia_api.py - Wikimedia Commons API wrapper
"""
import requests
import time
import random

class WikimediaAPI:
    def __init__(self):
        self.base_url = "https://commons.wikimedia.org/w/api.php"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AgriSense-AI/1.0 (https://github.com/agrisense-ai) Python/requests'
        })
    
    def search_images(self, query, limit=5):
        """
        Search for images on Wikimedia Commons with fallback options
        """
        try:
            # First try actual search
            image_urls = self._search_wikimedia(query, limit)
            
            # If we got some results, return them
            if image_urls:
                return image_urls
            
            # If no results, generate reliable placeholder images
            return self._generate_placeholder_images(query, limit)
            
        except Exception as e:
            print(f"Wikimedia API error: {e}")
            # Always return placeholder images as fallback
            return self._generate_placeholder_images(query, limit)
    
    def _search_wikimedia(self, query, limit=5):
        """
        Internal method to search Wikimedia Commons
        """
        try:
            # Chuẩn hóa query và tạo nhiều từ khóa tìm kiếm
            query = query.lower().strip()
            
            # Map tiếng Việt sang tiếng Anh nếu cần
            vn_to_en = {
                'bò': 'cow cattle bovine',
                'gà': 'chicken poultry',
                'lợn': 'pig swine',
                'trâu': 'buffalo',
                'dê': 'goat',
                'cừu': 'sheep',
                'ngựa': 'horse',
                # Thêm các mapping khác nếu cần
            }
            
            # Sử dụng mapping nếu có
            search_query = vn_to_en.get(query, query)
            
            # Tạo các từ khóa tìm kiếm
            search_terms = [
                f'filetype:bitmap {search_query}',
                f'{search_query} agriculture',
                f'{search_query} farming',
                f'agricultural {search_query}',
                search_query  # Thêm từ khóa gốc
            ]
            
            for search_term in search_terms:
                search_params = {
                    'action': 'query',
                    'format': 'json',
                    'list': 'search',
                    'srsearch': search_term,
                    'srnamespace': 6,  # File namespace
                    'srlimit': limit * 3,  # Get more to filter
                    'srprop': 'title|snippet'
                }
                
                try:
                    response = self.session.get(self.base_url, params=search_params, timeout=30)  # Tăng timeout
                    response.raise_for_status()
                    
                    search_data = response.json()
                    
                    if 'query' not in search_data or 'search' not in search_data['query']:
                        print(f"No results for search term: {search_term}")
                        continue
                except Exception as e:
                    print(f"Error searching term {search_term}: {e}")
                    continue
                
                files = search_data['query']['search']
                image_urls = []
                
                for file_info in files[:limit]:
                    file_title = file_info['title']
                    
                    # Skip non-image files
                    if not any(ext in file_title.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                        continue
                    
                    try:
                        # Get image info and URL
                        info_params = {
                            'action': 'query',
                            'format': 'json',
                            'titles': file_title,
                            'prop': 'imageinfo',
                            'iiprop': 'url|size|mime',
                            'iiurlwidth': 400,
                            'iiurlheight': 300
                        }
                        
                        info_response = self.session.get(self.base_url, params=info_params, timeout=10)
                        info_response.raise_for_status()
                        
                        info_data = info_response.json()
                        
                        if 'query' in info_data and 'pages' in info_data['query']:
                            for page_id, page_info in info_data['query']['pages'].items():
                                if 'imageinfo' in page_info and page_info['imageinfo']:
                                    img_info = page_info['imageinfo'][0]
                                    
                                    # Check if it's a valid image with working URL
                                    if ('url' in img_info and 
                                        'thumburl' in img_info and
                                        img_info.get('mime', '').startswith('image/')):
                                        
                                        # Use thumbnail URL for better performance
                                        image_url = img_info.get('thumburl', img_info['url'])
                                        
                                        image_urls.append({
                                            'url': image_url,
                                            'description': file_title.replace('File:', '').replace('.jpg', '').replace('.png', '').replace('.jpeg', ''),
                                            'photographer': 'Wikimedia Commons'
                                        })
                                        
                                        if len(image_urls) >= limit:
                                            break
                        
                        # Add small delay between requests
                        time.sleep(0.2)
                        
                    except Exception as e:
                        print(f"Error processing file {file_title}: {e}")
                        continue
                
                # If we found enough images, return them
                if len(image_urls) >= limit:
                    return image_urls[:limit]
                
                # Add delay between search attempts
                time.sleep(0.5)
            
            return image_urls
            
        except Exception as e:
            print(f"Wikimedia search error: {e}")
            return []
    
    def _generate_placeholder_images(self, query, limit=5):
        """
        Generate reliable placeholder images when real search fails
        """
        placeholders = []
        
        # Create diverse placeholder images
        colors = ['10b981', '3b82f6', 'f59e0b', 'ef4444', '8b5cf6']
        
        for i in range(limit):
            color = colors[i % len(colors)]
            
            # Use multiple placeholder services for reliability
            placeholder_options = [
                f"https://via.placeholder.com/400x300/{color}/ffffff?text={query.replace(' ', '+')}+{i+1}",
                f"https://picsum.photos/400/300?random={int(time.time()) + i}",
                f"https://source.unsplash.com/400x300/?agriculture,farming,{query.replace(' ', ',')}&sig={i}"
            ]
            
            placeholders.append({
                'url': placeholder_options[0],  # Primary placeholder
                'backup_urls': placeholder_options[1:],  # Backup options
                'description': f'{query} - Hình ảnh {i+1}',
                'photographer': 'AgriSense AI'
            })
        
        return placeholders
    
    def get_multiple_image_urls(self, filenames):
        """
        Get URLs for multiple image files efficiently using batch API
        """
        if not filenames:
            return {}
        
        # Prepare titles for batch query
        titles = '|'.join([f'File:{filename}' if not filename.startswith('File:') else filename for filename in filenames])
        
        try:
            params = {
                'action': 'query',
                'format': 'json',
                'titles': titles,
                'prop': 'imageinfo',
                'iiprop': 'url|size|mime',
                'iiurlwidth': 400,
                'iiurlheight': 300
            }
            
            response = self.session.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            urls_map = {}
            
            if 'query' in data and 'pages' in data['query']:
                for page_id, page_info in data['query']['pages'].items():
                    if 'imageinfo' in page_info and page_info['imageinfo']:
                        img_info = page_info['imageinfo'][0]
                        
                        # Get filename from title
                        title = page_info.get('title', '')
                        filename = title.replace('File:', '') if title.startswith('File:') else title
                        
                        # Check if it's a valid image with working URL
                        if ('url' in img_info and 
                            img_info.get('mime', '').startswith('image/')):
                            
                            # Use thumbnail URL for better performance
                            image_url = img_info.get('thumburl', img_info['url'])
                            urls_map[filename] = image_url
            
            return urls_map
            
        except Exception as e:
            print(f"Error getting multiple image URLs: {e}")
            return {}
    
    def search_images_by_category(self, category, limit=5):
        """
        Search for images in a specific category
        """
        try:
            # Search for images in the category
            search_params = {
                'action': 'query',
                'format': 'json',
                'list': 'categorymembers',
                'cmtitle': f'Category:{category}',
                'cmnamespace': 6,  # File namespace
                'cmlimit': limit * 2,
                'cmtype': 'file'
            }
            
            response = self.session.get(self.base_url, params=search_params, timeout=10)
            response.raise_for_status()
            
            search_data = response.json()
            
            if 'query' not in search_data or 'categorymembers' not in search_data['query']:
                return []
            
            files = search_data['query']['categorymembers']
            image_urls = []
            
            for file_info in files[:limit]:
                file_title = file_info['title']
                
                # Get image info and URL
                info_params = {
                    'action': 'query',
                    'format': 'json',
                    'titles': file_title,
                    'prop': 'imageinfo',
                    'iiprop': 'url|size|mime',
                    'iiurlwidth': 400,
                    'iiurlheight': 300
                }
                
                info_response = self.session.get(self.base_url, params=info_params, timeout=10)
                info_response.raise_for_status()
                
                info_data = info_response.json()
                
                if 'query' in info_data and 'pages' in info_data['query']:
                    for page_id, page_info in info_data['query']['pages'].items():
                        if 'imageinfo' in page_info and page_info['imageinfo']:
                            img_info = page_info['imageinfo'][0]
                            
                            # Check if it's a valid image
                            if ('url' in img_info and 
                                img_info.get('mime', '').startswith('image/')):
                                
                                # Use thumbnail URL for better performance
                                image_url = img_info.get('thumburl', img_info['url'])
                                
                                image_urls.append({
                                    'url': image_url,
                                    'description': file_title.replace('File:', '').replace('.jpg', '').replace('.png', '').replace('.jpeg', ''),
                                    'photographer': 'Wikimedia Commons'
                                })
                
                # Add small delay between requests
                time.sleep(0.2)
            
            return image_urls
            
        except Exception as e:
            print(f"Category search error: {e}")
            return []
    
    def get_image_info(self, filename):
        """
        Get detailed information about an image file
        """
        try:
            params = {
                'action': 'query',
                'format': 'json',
                'titles': filename,
                'prop': 'imageinfo',
                'iiprop': 'url|size|mime|user|comment'
            }
            
            response = self.session.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            if 'query' in data and 'pages' in data['query']:
                for page_id, page_info in data['query']['pages'].items():
                    if 'imageinfo' in page_info and page_info['imageinfo']:
                        return page_info['imageinfo'][0]
            
            return None
            
        except Exception as e:
            print(f"Error getting image info: {e}")
            return None