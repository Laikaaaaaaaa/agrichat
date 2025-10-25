"""
RSS News API - Backend service for loading news from Vietnamese sources
This bypasses CORS issues and uses proper HTTP headers to fetch RSS feeds
"""

import os
import requests
import json
import time
import logging
from datetime import datetime
from xml.etree import ElementTree as ET
from urllib.parse import urlparse
from functools import lru_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# HTTP Headers to avoid being blocked by websites
RSS_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www.google.com/',
    'DNT': '1'
}

class RSSNewsAPI:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour cache
        
        self.vietnamese_feeds = [
            # Nông nghiệp môi trường
            {"name": "Nông nghiệp Môi trường - Chăn nuôi", "url": "https://nongnghiepmoitruong.vn/chan-nuoi.rss", "category": "livestock"},
            {"name": "Nông nghiệp Môi trường - Tái cơ cấu", "url": "https://nongnghiepmoitruong.vn/tai-co-cau-nong-nghiep.rss", "category": "agriculture"},
            {"name": "Nông nghiệp Môi trường - Khuyến nông", "url": "https://nongnghiepmoitruong.vn/khuyen-nong.rss", "category": "agriculture"},
            {"name": "Nông nghiệp Môi trường - KHCN", "url": "https://nongnghiepmoitruong.vn/khoa-hoc---cong-nghe.rss", "category": "technology"},
            
            # VnExpress
            {"name": "VnExpress - Nông nghiệp", "url": "https://vnexpress.net/tag/nong-nghiep.rss", "category": "agriculture"},
            {"name": "VnExpress - Khoa học", "url": "https://vnexpress.net/rss/khoa-hoc.rss", "category": "technology"},
            {"name": "VnExpress - Thời sự", "url": "https://vnexpress.net/rss/thoi-su.rss", "category": "news"},
            {"name": "VnExpress - Kinh doanh", "url": "https://vnexpress.net/rss/kinh-doanh.rss", "category": "business"},
            
            # Tuổi Trẻ
            {"name": "Tuổi Trẻ - Khoa học", "url": "https://tuoitre.vn/rss/khoa-hoc.rss", "category": "technology"},
            {"name": "Tuổi Trẻ - Thời sự", "url": "https://tuoitre.vn/rss/thoisu.rss", "category": "news"},
            {"name": "Tuổi Trẻ - Kinh tế", "url": "https://tuoitre.vn/rss/kinhte.rss", "category": "economy"},
            
            # Thanh Niên
            {"name": "Thanh Niên - Kinh tế", "url": "https://thanhnien.vn/rss/kinh-te.rss", "category": "economy"},
            {"name": "Thanh Niên - Đời sống", "url": "https://thanhnien.vn/rss/doi-song.rss", "category": "lifestyle"},
            
            # Dân trí
            {"name": "Dân Trí - Nông nghiệp", "url": "https://dantri.com.vn/rss/nong-nghiep.rss", "category": "agriculture"},
            {"name": "Dân Trí - Kinh doanh", "url": "https://dantri.com.vn/rss/kinh-doanh.rss", "category": "business"},
            
            # VietnamNet
            {"name": "VietnamNet - Khoa học", "url": "https://vietnamnet.vn/rss/khoa-hoc.rss", "category": "technology"},
            {"name": "VietnamNet - Môi trường", "url": "https://vietnamnet.vn/rss/moi-truong.rss", "category": "climate"},
            
            # Zing News
            {"name": "Zing News - Kinh doanh", "url": "https://zingnews.vn/rss/kinh-doanh.rss", "category": "business"},
            {"name": "Zing News - Khoa học", "url": "https://zingnews.vn/rss/khoa-hoc.rss", "category": "technology"},
        ]

    def fetch_rss_feed(self, feed_url, timeout=10):
        """Fetch RSS feed with proper headers"""
        try:
            logger.info(f"📡 Fetching: {feed_url}")
            response = requests.get(feed_url, headers=RSS_HEADERS, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.text
        except requests.exceptions.Timeout:
            logger.warning(f"⏱️ Timeout: {feed_url}")
            return None
        except requests.exceptions.ConnectionError:
            logger.warning(f"🔌 Connection error: {feed_url}")
            return None
        except Exception as e:
            logger.warning(f"❌ Error fetching {feed_url}: {e}")
            return None

    def parse_rss_xml(self, xml_text):
        """Parse RSS XML and extract items"""
        try:
            if not xml_text:
                return []
            
            root = ET.fromstring(xml_text)
            namespaces = {
                'content': 'http://purl.org/rss/1.0/modules/content/',
                'atom': 'http://www.w3.org/2005/Atom',
                'media': 'http://search.yahoo.com/mrss/'
            }
            
            items = []
            
            # Try RSS format
            for item in root.findall('.//item'):
                title_elem = item.find('title')
                link_elem = item.find('link')
                desc_elem = item.find('description')
                pubdate_elem = item.find('pubDate')
                content_elem = item.find('content:encoded', namespaces)
                
                title = (title_elem.text or '').strip() if title_elem is not None else ''
                link = (link_elem.text or '').strip() if link_elem is not None else ''
                description = (desc_elem.text or '').strip() if desc_elem is not None else ''
                pubdate = (pubdate_elem.text or '').strip() if pubdate_elem is not None else ''
                
                # Clean HTML from description
                description = description.replace('<![CDATA[', '').replace(']]>', '')
                description = description[:500]  # Limit length
                
                if title and link:
                    items.append({
                        'title': title,
                        'link': link,
                        'description': description,
                        'pubDate': pubdate,
                    })
            
            logger.info(f"✅ Parsed {len(items)} items")
            return items
        except Exception as e:
            logger.warning(f"❌ Parse error: {e}")
            return []

    def load_news_from_feeds(self, limit=50):
        """Load news from multiple RSS feeds"""
        all_news = []
        
        for feed in self.vietnamese_feeds:
            try:
                # Check cache first
                cache_key = f"feed_{feed['url']}"
                cached = self.get_from_cache(cache_key)
                
                if cached:
                    logger.info(f"✅ Cache hit for {feed['name']}")
                    all_news.extend(cached)
                    continue
                
                # Fetch and parse
                xml_text = self.fetch_rss_feed(feed['url'])
                if xml_text:
                    items = self.parse_rss_xml(xml_text)
                    
                    # Add category and source
                    for item in items:
                        item['category'] = feed['category']
                        item['source'] = feed['name']
                        item['isVietnamese'] = True
                    
                    # Cache the results
                    self.set_cache(cache_key, items)
                    all_news.extend(items)
                    logger.info(f"✅ Loaded {len(items)} from {feed['name']}")
                    
                    # Stop if we have enough
                    if len(all_news) >= limit:
                        break
                        
            except Exception as e:
                logger.error(f"Error loading {feed['name']}: {e}")
                continue
        
        # Sort by date
        try:
            all_news.sort(key=lambda x: datetime.fromisoformat(x['pubDate'].replace('Z', '+00:00')), reverse=True)
        except:
            pass
        
        return all_news[:limit]

    def get_from_cache(self, key):
        """Get from cache if not expired"""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry['timestamp'] < self.cache_ttl:
                return entry['data']
            else:
                del self.cache[key]
        return None

    def set_cache(self, key, data):
        """Set cache"""
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }

# Create global instance
news_api = RSSNewsAPI()

def get_news(limit=50):
    """Get news from all feeds"""
    return news_api.load_news_from_feeds(limit)

def get_news_by_category(category, limit=20):
    """Get news by specific category"""
    all_news = news_api.load_news_from_feeds(limit * 3)
    return [item for item in all_news if item.get('category') == category][:limit]
