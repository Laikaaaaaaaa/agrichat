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
            # Nông nghiệp môi trường - 9 feeds
            {"name": "Nông nghiệp Môi trường - Chăn nuôi", "url": "https://nongnghiepmoitruong.vn/chan-nuoi.rss", "category": "livestock", "filter": False},
            {"name": "Nông nghiệp Môi trường - Tái cơ cấu", "url": "https://nongnghiepmoitruong.vn/tai-co-cau-nong-nghiep.rss", "category": "agriculture", "filter": False},
            {"name": "Nông nghiệp Môi trường - Khuyến nông", "url": "https://nongnghiepmoitruong.vn/khuyen-nong.rss", "category": "agriculture", "filter": False},
            {"name": "Nông nghiệp Môi trường - KHCN", "url": "https://nongnghiepmoitruong.vn/khoa-hoc---cong-nghe.rss", "category": "technology", "filter": False},
            {"name": "Nông nghiệp Môi trường - Thị trường", "url": "https://nongnghiepmoitruong.vn/thi-truong.rss", "category": "agriculture", "filter": False},
            {"name": "Nông nghiệp Môi trường - Kinh doanh", "url": "https://nongnghiepmoitruong.vn/kinh-doanh.rss", "category": "agriculture", "filter": False},
            {"name": "Nông nghiệp Môi trường - Thời sự", "url": "https://nongnghiepmoitruong.vn/thoi-su.rss", "category": "agriculture", "filter": False},
            {"name": "Nông nghiệp Môi trường - Video", "url": "https://nongnghiepmoitruong.vn/video.rss", "category": "agriculture", "filter": False},
            {"name": "Nông nghiệp Môi trường - Tất cả", "url": "https://nongnghiepmoitruong.vn/rss", "category": "agriculture", "filter": False},
        
            # Moitruong.net.vn - 5 feeds
            {"name": "Môi trường - Biến đổi khí hậu", "url": "https://moitruong.net.vn/rss/tin-tuc/bien-doi-khi-hau", "category": "climate", "filter": False},
            {"name": "Môi trường - An ninh nguồn nước", "url": "https://moitruong.net.vn/rss/nuoc-va-cuoc-song/an-ninh-nguon-nuoc", "category": "climate", "filter": False},
            {"name": "Môi trường - Ô nhiễm", "url": "https://moitruong.net.vn/rss/moi-truong-tai-nguyen/o-nhiem-moi-truong", "category": "climate", "filter": False},
            {"name": "Môi trường - Vấn đề hôm nay", "url": "https://moitruong.net.vn/rss/tin-tuc/van-de-hom-nay", "category": "climate", "filter": False},
            {"name": "Môi trường - Kinh tế xanh", "url": "https://moitruong.net.vn/rss/kinh-te-xanh/chuyen-doi-xanh", "category": "climate", "filter": False},
            
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

    def load_news_from_feeds(self, limit=50, offset=0):
        """
        Load news from multiple RSS feeds (with concurrent fetching for speed)
        - Minimum: 50 articles
        - Maximum: 250 articles
        - Load feeds in PARALLEL to avoid blocking
        - Include 'has_more' flag and notification
        """
        import concurrent.futures
        import threading
        
        MIN_ARTICLES = 50
        MAX_ARTICLES = 250
        
        # Ensure limit is within bounds
        if limit < MIN_ARTICLES:
            limit = MIN_ARTICLES
        if limit > MAX_ARTICLES:
            limit = MAX_ARTICLES
        
        all_news = []
        feeds_loaded = 0
        failed_feeds = 0
        
        # ✅ OPTIMIZATION: Load feeds in PARALLEL using ThreadPoolExecutor
        # This prevents blocking on slow RSS feeds
        def load_single_feed_worker(feed):
            """Load a single RSS feed (called in thread pool)"""
            try:
                cache_key = f"feed_{feed['url']}"
                cached = self.get_from_cache(cache_key)
                
                if cached:
                    logger.info(f"✅ Cache hit for {feed['name']}")
                    return cached, True  # (items, is_cached)
                
                # Fetch RSS with timeout
                xml_text = self.fetch_rss_feed(feed['url'], timeout=8)
                if xml_text:
                    items = self.parse_rss_xml(xml_text, feed_config=feed)
                    items = self.filter_articles(items, feed)
                    items = items[:30]  # Get up to 30 per feed (we'll merge them)
                    
                    for item in items:
                        item['category'] = feed['category']
                        item['source'] = feed['name']
                        item['isVietnamese'] = True
                    
                    # Cache for next request
                    self.set_cache(cache_key, items)
                    logger.info(f"✅ Loaded {len(items)} from {feed['name']}")
                    return items, False
                else:
                    logger.warning(f"⚠️ Failed to fetch {feed['name']}")
                    return [], False
                    
            except Exception as e:
                logger.error(f"Error loading {feed['name']}: {e}")
                return [], False
        
        # ✅ Load feeds concurrently (max 5 threads to avoid overwhelming network)
        max_workers = min(5, len(self.vietnamese_feeds))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all feeds to thread pool
            future_to_feed = {
                executor.submit(load_single_feed_worker, feed): feed 
                for feed in self.vietnamese_feeds
            }
            
            # Collect results as they complete (not waiting for all)
            for future in concurrent.futures.as_completed(future_to_feed):
                items, is_cached = future.result()
                if items:
                    all_news.extend(items)
                    feeds_loaded += 1
                    logger.info(f"📊 Progress: {feeds_loaded} feeds loaded, {len(all_news)} total articles")
                    
                    # 🚀 EARLY RETURN: Once we have enough articles, return immediately
                    # Don't wait for all feeds - client gets fast response
                    if len(all_news) >= limit * 3:
                        logger.info(f"⚡ Early return: {len(all_news)} articles loaded (enough for {limit})")
                        break
                else:
                    failed_feeds += 1
        
        # Remove duplicates
        all_news = list({article.get('title'): article 
                        for article in all_news}.values())
        
        logger.info(f"📊 Feed loading complete: {len(all_news)} total articles, {feeds_loaded} feeds, {failed_feeds} failed")
        
        # Apply pagination with offset
        start_idx = offset
        end_idx = offset + limit
        paginated_news = all_news[start_idx:end_idx]
        
        # Determine if there are more articles available
        has_more = (end_idx < len(all_news))
        is_insufficient = (len(paginated_news) < MIN_ARTICLES)
        
        notification = None
        if is_insufficient and not has_more:
            # We've loaded all available articles but it's less than 50
            notification = f"⚠️ Chỉ có {len(all_news)} bài báo trong hệ thống. Hết báo!"
            logger.warning(f"⚠️ Insufficient articles: only {len(all_news)} out of minimum {MIN_ARTICLES}")
        elif end_idx >= len(all_news) and len(all_news) >= MIN_ARTICLES:
            # We've reached the end with enough articles
            notification = f"✅ Đã tải hết {len(all_news)} bài báo trong hệ thống"
            has_more = False
        
        logger.info(f"📊 Returned {len(paginated_news)} articles from {len(all_news)} total (offset={offset}, has_more={has_more})")
        
        return {
            'articles': paginated_news,
            'total': len(all_news),
            'count': len(paginated_news),
            'has_more': has_more,
            'notification': notification,
            'insufficient': is_insufficient
        }

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

def get_news(limit=50, offset=0):
    """Get news from all feeds with pagination"""
    result = news_api.load_news_from_feeds(limit, offset)
    return result

def get_news_by_category(category, limit=20, offset=0):
    """Get news by specific category with pagination"""
    result = news_api.load_news_from_feeds(min(250, limit * 5), offset=0)
    articles = result['articles']
    
    # Filter by category
    category_news = [item for item in articles if item.get('category') == category]
    
    # Apply pagination to filtered results
    start_idx = offset
    end_idx = offset + limit
    paginated = category_news[start_idx:end_idx]
    
    has_more = (end_idx < len(category_news))
    notification = None
    
    if len(paginated) < limit and not has_more and len(category_news) > 0:
        notification = f"✅ Đã tải hết {len(category_news)} bài báo trong chuyên mục '{category}'"
    
    return {
        'articles': paginated,
        'total': len(category_news),
        'count': len(paginated),
        'has_more': has_more,
        'notification': notification
    }
