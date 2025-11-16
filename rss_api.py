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
from email.utils import parsedate_to_datetime

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
        
        # Keywords to filter agriculture/environment related articles
        self.agriculture_keywords = [
            'nông nghiệp', 'nông dân', 'trồng trọt', 'cây trồng', 'lúa', 'gạo', 'rau', 'hoa',
            'chăn nuôi', 'bò', 'heo', 'gà', 'vịt', 'trâu', 'gia súc', 'gia cầm',
            'thủy sản', 'cá', 'tôm', 'cua', 'nuôi trồng thủy sản',
            'máy nông nghiệp', 'công nghệ nông nghiệp', 'nông sản', 'xuất khẩu nông sản',
            'môi trường', 'khí hậu', 'sinh thái', 'đất đai', 'tài nguyên nước',
            'bệnh cây trồng', 'sâu bệnh', 'phòng trừ sâu bệnh',
            'phân bón', 'thuốc', 'hạt giống', 'giống cây',
            'trang trại', 'vườn', 'ruộng', 'cánh đồng',
            'an toàn thực phẩm', 'thực phẩm sạch', 'nông nghiệp hữu cơ'
        ]
        
        self.vietnamese_feeds = [
            # Nông nghiệp môi trường - NO FILTER (accept ALL - thời sự, kinh doanh, v.v. đều liên quan NN&MT)
            {"name": "Nông nghiệp Môi trường - Chăn nuôi", "url": "https://nongnghiepmoitruong.vn/chan-nuoi.rss", "category": "livestock", "filter": False},
            {"name": "Nông nghiệp Môi trường - Tái cơ cấu", "url": "https://nongnghiepmoitruong.vn/tai-co-cau-nong-nghiep.rss", "category": "agriculture", "filter": False},
            {"name": "Nông nghiệp Môi trường - Khuyến nông", "url": "https://nongnghiepmoitruong.vn/khuyen-nong.rss", "category": "agriculture", "filter": False},
            {"name": "Nông nghiệp Môi trường - KHCN", "url": "https://nongnghiepmoitruong.vn/khoa-hoc---cong-nghe.rss", "category": "technology", "filter": False},
            {"name": "Nông nghiệp Môi trường - Thị trường", "url": "https://nongnghiepmoitruong.vn/thi-truong.rss", "category": "agriculture", "filter": False},
            {"name": "Nông nghiệp Môi trường - Kinh doanh", "url": "https://nongnghiepmoitruong.vn/kinh-doanh.rss", "category": "agriculture", "filter": False},
            {"name": "Nông nghiệp Môi trường - Thời sự", "url": "https://nongnghiepmoitruong.vn/thoi-su.rss", "category": "agriculture", "filter": False},
            {"name": "Nông nghiệp Môi trường - Video", "url": "https://nongnghiepmoitruong.vn/video.rss", "category": "agriculture", "filter": False},
            {"name": "Nông nghiệp Môi trường - Tất cả", "url": "https://nongnghiepmoitruong.vn/rss", "category": "agriculture", "filter": False},
            
            # VnExpress - NO FILTER (load tất cả để có bài xen kẽ)
            {"name": "VnExpress - Nông nghiệp", "url": "https://vnexpress.net/tag/nong-nghiep.rss", "category": "agriculture", "filter": False},
            {"name": "VnExpress - Khoa học", "url": "https://vnexpress.net/rss/khoa-hoc.rss", "category": "technology", "filter": False},
            
            # Tuổi Trẻ - NO FILTER
            {"name": "Tuổi Trẻ - Khoa học", "url": "https://tuoitre.vn/rss/khoa-hoc.rss", "category": "technology", "filter": False},
            
            # VietnamNet - NO FILTER
            {"name": "VietnamNet - Khoa học", "url": "https://vietnamnet.vn/rss/khoa-hoc.rss", "category": "technology", "filter": False},
            {"name": "VietnamNet - Môi trường", "url": "https://vietnamnet.vn/rss/moi-truong.rss", "category": "climate", "filter": False},
            
            # Zing News - NO FILTER
            {"name": "Zing News - Khoa học", "url": "https://zingnews.vn/rss/khoa-hoc.rss", "category": "technology", "filter": False},
            
            # COA (Cộng đồng Nông nghiệp Hữu Cơ) - NO FILTER
            {"name": "COA - Tin tức", "url": "https://coa.org.vn/vi/news/rss/Tin-tuc/", "category": "agriculture", "filter": False},
            {"name": "COA - Tất cả", "url": "https://coa.org.vn/vi/news/rss/", "category": "agriculture", "filter": False},
            {"name": "COA - Nông nghiệp hữu cơ", "url": "https://coa.org.vn/vi/news/rss/nong-nghiep-huu-co/", "category": "agriculture", "filter": False},
            {"name": "COA - Chứng nhận hữu cơ", "url": "https://coa.org.vn/vi/news/rss/chung-nhan-huu-co/", "category": "agriculture", "filter": False},
            
            # Ban Quản Lý Dự Án Dạo Công Nghiệp và Phát Triển Nông Thôn - Cà Mau
            {"name": "Cà Mau - Các dự án triển khai", "url": "https://banqldactnnptnt.camau.gov.vn/Rss.aspx?catid=47983&catname=cac-du-an-trien-khai&rec=50&sub=F&id=1396", "category": "agriculture", "filter": False},
            
            # VEPF (Vietnam Environment Protection Fund) - NO FILTER
            {"name": "VEPF - Tin tức", "url": "https://www.vepf.vn/vi/rss/tin-tuc-vepftpdhmy.rss", "category": "climate", "filter": False},
            {"name": "VEPF - Tin môi trường", "url": "https://www.vepf.vn/vi/rss/tin-moi-truong-vepfpw4e5j.rss", "category": "climate", "filter": False},
        ]

    def is_agriculture_related(self, title, description):
        """Check if article is related to agriculture/environment"""
        text = (title + ' ' + description).lower()
        
        # Check if any keyword matches
        for keyword in self.agriculture_keywords:
            if keyword in text:
                return True
        
        return False
    
    def filter_articles(self, articles, feed):
        """Filter articles based on feed configuration"""
        if not feed.get('filter', True):
            # No filter needed for this feed
            return articles
        
        # Filter articles to keep only agriculture/environment related ones
        filtered = []
        for article in articles:
            if self.is_agriculture_related(article.get('title', ''), article.get('description', '')):
                filtered.append(article)
        
        logger.info(f"🔍 Filtered {feed['name']}: {len(articles)} -> {len(filtered)} articles")
        return filtered

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

    def clean_html_text(self, text):
        """Clean HTML tags and entities from text"""
        if not text:
            return ''
        import re
        # Remove CDATA tags
        text = text.replace('<![CDATA[', '').replace(']]>', '')
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        import html
        text = html.unescape(text)
        # Clean up whitespace
        text = ' '.join(text.split())
        return text

    def parse_rss_xml(self, xml_text):
        """Parse RSS XML and extract items - handles both RSS 2.0 and Atom"""
        try:
            if not xml_text:
                return []
            
            # Try to parse XML
            try:
                root = ET.fromstring(xml_text)
            except ET.ParseError as e:
                logger.warning(f"XML parse error, trying fallback: {e}")
                # Try with encoding fix
                xml_text = xml_text.encode('utf-8', errors='ignore').decode('utf-8')
                root = ET.fromstring(xml_text)
            
            namespaces = {
                'content': 'http://purl.org/rss/1.0/modules/content/',
                'atom': 'http://www.w3.org/2005/Atom',
                'media': 'http://search.yahoo.com/mrss/',
                '': 'http://www.w3.org/2005/Atom'
            }
            
            items = []
            
            # Try RSS 2.0 format first
            for item in root.findall('.//item'):
                title_elem = item.find('title')
                link_elem = item.find('link')
                desc_elem = item.find('description')
                pubdate_elem = item.find('pubDate')
                
                title = (title_elem.text or '').strip() if title_elem is not None else ''
                link = (link_elem.text or '').strip() if link_elem is not None else ''
                description = (desc_elem.text or '').strip() if desc_elem is not None else ''
                pubdate = (pubdate_elem.text or '').strip() if pubdate_elem is not None else ''
                
                # Clean HTML from text
                title = self.clean_html_text(title)
                description = self.clean_html_text(description)
                description = description[:500]  # Limit length
                
                if title and link:
                    items.append({
                        'title': title,
                        'link': link,
                        'description': description,
                        'pubDate': pubdate,
                    })
            
            # If no items found, try Atom format
            if not items:
                logger.info("No RSS items found, trying Atom format...")
                for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
                    title_elem = entry.find('{http://www.w3.org/2005/Atom}title')
                    link_elem = entry.find('{http://www.w3.org/2005/Atom}link')
                    summary_elem = entry.find('{http://www.w3.org/2005/Atom}summary')
                    published_elem = entry.find('{http://www.w3.org/2005/Atom}published')
                    
                    title = (title_elem.text or '').strip() if title_elem is not None else ''
                    link = link_elem.get('href', '') if link_elem is not None else ''
                    description = (summary_elem.text or '').strip() if summary_elem is not None else ''
                    pubdate = (published_elem.text or '').strip() if published_elem is not None else ''
                    
                    # Clean HTML
                    title = self.clean_html_text(title)
                    description = self.clean_html_text(description)
                    description = description[:500]
                    
                    if title and link:
                        items.append({
                            'title': title,
                            'link': link,
                            'description': description,
                            'pubDate': pubdate,
                        })
            
            logger.info(f"✅ Parsed {len(items)} items from RSS/Atom")
            return items
            
        except Exception as e:
            logger.warning(f"❌ Parse error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def load_news_from_feeds(self, limit=50):
        """Load news from multiple RSS feeds - loads from MANY feeds to get variety"""
        all_news = []
        feeds_loaded = 0
        
        # Prioritize agriculture feeds first for better distribution
        sorted_feeds = sorted(self.vietnamese_feeds, 
                            key=lambda f: (0 if f['category'] in ['agriculture', 'livestock', 'technology'] else 1))
        
        for feed in sorted_feeds:
            # Load enough to reach limit (but continue to load from different feeds)
            if len(all_news) >= limit * 2:  # Load 2x limit to ensure variety
                break
                
            try:
                # Check cache first
                cache_key = f"feed_{feed['url']}"
                cached = self.get_from_cache(cache_key)
                
                if cached:
                    logger.info(f"✅ Cache hit for {feed['name']}")
                    all_news.extend(cached)
                    feeds_loaded += 1
                    continue
                
                # Fetch and parse
                xml_text = self.fetch_rss_feed(feed['url'])
                if xml_text:
                    items = self.parse_rss_xml(xml_text)
                    
                    # Apply filter if needed
                    items = self.filter_articles(items, feed)
                    
                    # Limit items per feed to ensure diversity
                    items = items[:30]
                    
                    # Add category and source
                    for item in items:
                        item['category'] = feed['category']
                        item['source'] = feed['name']
                        item['isVietnamese'] = True
                    
                    # Cache the results
                    self.set_cache(cache_key, items)
                    all_news.extend(items)
                    feeds_loaded += 1
                    logger.info(f"✅ Loaded {len(items)} from {feed['name']} (category: {feed['category']})")
                        
            except Exception as e:
                logger.error(f"Error loading {feed['name']}: {e}")
                continue
        
        # Sort by date (try to handle various date formats)
        try:
            def parse_date(date_str):
                if not date_str:
                    return datetime.now()
                try:
                    # Try ISO format first
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except:
                    try:
                        # Try RFC2822 format (RSS standard)
                        return parsedate_to_datetime(date_str)
                    except:
                        return datetime.now()
            
            all_news.sort(key=lambda x: parse_date(x.get('pubDate', '')), reverse=True)
        except Exception as e:
            logger.warning(f"Error sorting by date: {e}")
        
        logger.info(f"📊 Loaded {len(all_news)} total articles from {feeds_loaded} feeds")
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
    """Get news by specific category - loads enough to fill the category"""
    # Load 3x limit to ensure we get enough for the category
    all_news = news_api.load_news_from_feeds(min(150, limit * 5))
    
    # Filter by category
    category_news = [item for item in all_news if item.get('category') == category]
    
    logger.info(f"🔍 Category '{category}': found {len(category_news)} from {len(all_news)} total")
    
    return category_news[:limit]
