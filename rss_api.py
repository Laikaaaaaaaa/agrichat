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
            # ✅ Nông nghiệp Môi trường - 43 feeds (comprehensive coverage)
            {"name": "Nông Môi - Chính trị", "url": "https://nongnghiepmoitruong.vn/chinh-tri.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Thời sự NN-MT", "url": "https://nongnghiepmoitruong.vn/thoi-su-nong-nghiep-moi-truong.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Chăn nuôi", "url": "https://nongnghiepmoitruong.vn/chan-nuoi.rss", "category": "livestock", "filter": False},
            {"name": "Nông Môi - Thú y", "url": "https://nongnghiepmoitruong.vn/thu-y.rss", "category": "livestock", "filter": False},
            {"name": "Nông Môi - Trồng trọt", "url": "https://nongnghiepmoitruong.vn/trong-trot.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Khuyến nông", "url": "https://nongnghiepmoitruong.vn/khuyen-nong.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Tái cơ cấu", "url": "https://nongnghiepmoitruong.vn/tai-co-cau-nong-nghiep.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - KHCN", "url": "https://nongnghiepmoitruong.vn/khoa-hoc---cong-nghe.rss", "category": "technology", "filter": False},
            {"name": "Nông Môi - Thủy sản", "url": "https://nongnghiepmoitruong.vn/thuy-san.rss", "category": "livestock", "filter": False},
            {"name": "Nông Môi - Lâm nghiệp", "url": "https://nongnghiepmoitruong.vn/lam-nghiep.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Câu chuyện MT", "url": "https://nongnghiepmoitruong.vn/cau-chuyen-moi-truong.rss", "category": "climate", "filter": False},
            {"name": "Nông Môi - Quản lý chất thải", "url": "https://nongnghiepmoitruong.vn/quan-ly-chat-thai-ran.rss", "category": "climate", "filter": False},
            {"name": "Nông Môi - BĐKH", "url": "https://nongnghiepmoitruong.vn/bien-doi-khi-hau-moitruong.rss", "category": "climate", "filter": False},
            {"name": "Nông Môi - Khoáng sản", "url": "https://nongnghiepmoitruong.vn/khoang-san.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Tài nguyên nước", "url": "https://nongnghiepmoitruong.vn/tai-nguyen-nuoc.rss", "category": "climate", "filter": False},
            {"name": "Nông Môi - Biển đảo", "url": "https://nongnghiepmoitruong.vn/bien-dao.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - BĐS nông thôn", "url": "https://nongnghiepmoitruong.vn/bat-dong-san-nong-thon.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - BĐS du lịch", "url": "https://nongnghiepmoitruong.vn/bat-dong-san-du-lich.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Đô thị & đời sống", "url": "https://nongnghiepmoitruong.vn/do-thi-va-doi-song.rss", "category": "climate", "filter": False},
            {"name": "Nông Môi - Quy hoạch", "url": "https://nongnghiepmoitruong.vn/quy-hoach.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Chính sách đất đai", "url": "https://nongnghiepmoitruong.vn/chinh-sach-datdai.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Kinh tế thị trường", "url": "https://nongnghiepmoitruong.vn/kinh-te-thi-truong.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Việc làm", "url": "https://nongnghiepmoitruong.vn/viec-lam.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Doanh nghiệp", "url": "https://nongnghiepmoitruong.vn/doanh-nghiep-doanh-nhan.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Đầu tư tài chính", "url": "https://nongnghiepmoitruong.vn/dau-tu-tai-chinh.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Công khai ngân sách", "url": "https://nongnghiepmoitruong.vn/cong-khai-ngan-sach.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Cảnh sát MT", "url": "https://nongnghiepmoitruong.vn/canh-sat-moi-truong.rss", "category": "climate", "filter": False},
            {"name": "Nông Môi - An ninh trật tự", "url": "https://nongnghiepmoitruong.vn/an-ninh-trat-tu.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Văn bản mới", "url": "https://nongnghiepmoitruong.vn/van-ban-moi.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Những mảnh đời bất hạnh", "url": "https://nongnghiepmoitruong.vn/nhung-manh-doi-bat-hanh.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Nông sản Việt", "url": "https://nongnghiepmoitruong.vn/nong-san-viet-nong-nghiep-40.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Sản vật địa phương", "url": "https://nongnghiepmoitruong.vn/san-vat-dia-phuong.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Nông sản hữu cơ", "url": "https://nongnghiepmoitruong.vn/organic.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Tài chính", "url": "https://nongnghiepmoitruong.vn/tai-chinh.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Phân bón", "url": "https://nongnghiepmoitruong.vn/phan-bon.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Thuốc bảo vệ", "url": "https://nongnghiepmoitruong.vn/thuoc-bao-ve-thuc-vat.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Thức ăn gia súc", "url": "https://nongnghiepmoitruong.vn/thuc-an-chan-nuoi.rss", "category": "livestock", "filter": False},
            {"name": "Nông Môi - Thuốc thú y", "url": "https://nongnghiepmoitruong.vn/thuoc-thu-y.rss", "category": "livestock", "filter": False},
            {"name": "Nông Môi - Mô hình hay NTM", "url": "https://nongnghiepmoitruong.vn/mo-hinh-hay-ntm.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - BĐKH", "url": "https://nongnghiepmoitruong.vn/bien-doi-khi-hau.rss", "category": "climate", "filter": False},
            {"name": "Nông Môi - Chuyên nhỏ khởi nghiệp", "url": "https://nongnghiepmoitruong.vn/chuyen-nho-khoi-nghiep.rss", "category": "agriculture", "filter": False},
            {"name": "Nông Môi - Trí thức ngành nông", "url": "https://nongnghiepmoitruong.vn/tri-thuc-nghe-nong.rss", "category": "agriculture", "filter": False},
        
            # Báo lớn - 4 feeds
            {"name": "VnExpress", "url": "https://rss.vnexpress.net/", "category": "agriculture", "filter": True},
            {"name": "Tuổi Trẻ", "url": "https://tuoitre.vn/rss/", "category": "agriculture", "filter": True},
            {"name": "VietnamNet", "url": "https://vietnamnet.vn/rss/", "category": "agriculture", "filter": True},
            {"name": "Thanh Niên", "url": "https://thanhnien.vn/rss/", "category": "agriculture", "filter": True},
            
            # ✅ Dân Trí - Has images in HTML description
            {"name": "Dân Trí - Đời sống", "url": "https://dantri.com.vn/rss/doi-song.rss", "category": "agriculture", "filter": True, "extract_image": True},
        ]

    def is_agriculture_related(self, title, description):
        """Check if article is related to agriculture/environment"""
        text = (title + ' ' + description).lower()
        for keyword in self.agriculture_keywords:
            if keyword in text:
                return True
        return False
    
    def filter_articles(self, articles, feed):
        """Filter articles based on feed configuration"""
        if not feed.get('filter', True):
            return articles
        
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
        text = text.replace('<![CDATA[', '').replace(']]>', '')
        text = re.sub(r'<[^>]+>', '', text)
        import html
        text = html.unescape(text)
        text = ' '.join(text.split())
        return text

    def extract_image_from_html(self, html_text):
        """✅ Extract image URL from HTML description (for Dân Trí)"""
        if not html_text:
            return None
        
        import re
        # Look for <img> tags with src attribute
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
        matches = re.findall(img_pattern, html_text)
        
        if matches:
            # Return first image found
            image_url = matches[0]
            logger.info(f"✅ Extracted image from HTML: {image_url[:80]}...")
            return image_url
        
        return None

    def parse_rss_xml(self, xml_text, feed_config=None):
        """Parse RSS XML and extract items
        
        Args:
            xml_text: RSS XML content
            feed_config: Feed configuration dict (optional, for special handling like Dân Trí)
        """
        try:
            if not xml_text:
                return []
            
            try:
                root = ET.fromstring(xml_text)
            except ET.ParseError as e:
                logger.warning(f"XML parse error: {e}")
                xml_text = xml_text.encode('utf-8', errors='ignore').decode('utf-8')
                root = ET.fromstring(xml_text)
            
            items = []
            extract_image = feed_config and feed_config.get('extract_image', False)
            
            # RSS 2.0 format
            for item in root.findall('.//item'):
                title_elem = item.find('title')
                link_elem = item.find('link')
                desc_elem = item.find('description')
                pubdate_elem = item.find('pubDate')
                
                title = (title_elem.text or '').strip() if title_elem is not None else ''
                link = (link_elem.text or '').strip() if link_elem is not None else ''
                description = (desc_elem.text or '').strip() if desc_elem is not None else ''
                pubdate = (pubdate_elem.text or '').strip() if pubdate_elem is not None else ''
                
                # ✅ For Dân Trí, extract image from HTML before cleaning
                image_url = None
                if extract_image and description:
                    image_url = self.extract_image_from_html(description)
                
                title = self.clean_html_text(title)
                description = self.clean_html_text(description)
                description = description[:500]
                
                if title and link:
                    item_data = {
                        'title': title,
                        'link': link,
                        'description': description,
                        'pubDate': pubdate,
                    }
                    
                    # ✅ Add image URL if found
                    if image_url:
                        item_data['image_url'] = image_url
                    
                    items.append(item_data)
            
            logger.info(f"✅ Parsed {len(items)} items" + (f" with images extraction" if extract_image else ""))
            return items
            
        except Exception as e:
            logger.warning(f"❌ Parse error: {e}")
            return []

    def load_news_from_feeds(self, limit=50):
        """Load news from multiple RSS feeds"""
        all_news = []
        feeds_loaded = 0
        
        for feed in self.vietnamese_feeds:
            if len(all_news) >= limit * 2:
                break
                
            try:
                cache_key = f"feed_{feed['url']}"
                cached = self.get_from_cache(cache_key)
                
                if cached:
                    logger.info(f"✅ Cache hit for {feed['name']}")
                    all_news.extend(cached)
                    feeds_loaded += 1
                    continue
                
                xml_text = self.fetch_rss_feed(feed['url'])
                if xml_text:
                    # ✅ Pass feed config for special handling (e.g., Dân Trí image extraction)
                    items = self.parse_rss_xml(xml_text, feed_config=feed)
                    items = self.filter_articles(items, feed)
                    items = items[:30]
                    
                    for item in items:
                        item['category'] = feed['category']
                        item['source'] = feed['name']
                        item['isVietnamese'] = True
                    
                    self.set_cache(cache_key, items)
                    all_news.extend(items)
                    feeds_loaded += 1
                    logger.info(f"✅ Loaded {len(items)} from {feed['name']}")
                        
            except Exception as e:
                logger.error(f"Error loading {feed['name']}: {e}")
                continue
        
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
        self.cache[key] = {'data': data, 'timestamp': time.time()}

# Create global instance
news_api = RSSNewsAPI()

def get_news(limit=50):
    """Get news from all feeds"""
    return news_api.load_news_from_feeds(limit)

def get_news_by_category(category, limit=20):
    """Get news by specific category"""
    all_news = news_api.load_news_from_feeds(min(150, limit * 5))
    category_news = [item for item in all_news if item.get('category') == category]
    return category_news[:limit]
