"""
Image Search Memory Module
Quản lý lịch sử tìm kiếm ảnh để xử lý requests như "ảnh khác", "ảnh tiếp theo", etc.
💾 NOW PERSISTS TO DATABASE - survives server restarts!
"""

import logging
import json
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
import os

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agrichat.db')


class ImageSearchMemory:
    """
    Lưu trữ thông tin về lần tìm ảnh cuối cùng của user
    Để xử lý các request như "ảnh khác", "ảnh tiếp theo", etc.
    ✅ NOW PERSISTS TO DATABASE for reliability across restarts
    """
    
    def __init__(self):
        """Khởi tạo memory - per user (in-RAM cache + database backup)"""
        # Format: {user_id: {
        #   'query': 'con bò',
        #   'images': [{'url': '...', 'id': '...', ...}, ...],
        #   'sent_image_ids': set(),  # IDs của ảnh đã gửi
        #   'last_search_time': datetime,
        #   'search_count': int
        # }}
        self.memory = {}
    
    def _get_db_connection(self):
        """Get database connection"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logging.error(f"❌ Failed to connect to database: {e}")
            return None
    
    def save_search_result(self, user_id: str, query: str, images: List[Dict]):
        """
        Lưu kết quả tìm kiếm ảnh
        ✅ Saves to BOTH in-memory and database for persistence
        
        Args:
            user_id: ID người dùng
            query: Query tìm kiếm (ví dụ: "con bò")
            images: Danh sách ảnh tìm được
        """
        if not user_id or not query or not images:
            return
        
        # Save to in-memory cache
        self.memory[user_id] = {
            'query': query,
            'images': images,
            'sent_image_ids': set(),  # Chưa gửi ảnh nào
            'last_search_time': datetime.now(),
            'search_count': 1
        }
        
        logging.info(f"💾 Saved image search result for user {user_id}: '{query}' ({len(images)} images)")
        
        # Save to database for persistence
        try:
            conn = self._get_db_connection()
            if not conn:
                logging.warning("⚠️ Could not save to database (connection failed)")
                return
            
            cursor = conn.cursor()
            
            # Serialize images and sent_image_ids for storage
            images_json = json.dumps(images, ensure_ascii=False)
            sent_ids_json = json.dumps([], ensure_ascii=False)  # Start with empty sent IDs
            
            cursor.execute('''
                INSERT OR REPLACE INTO image_search_history 
                (user_id, query, images_json, sent_image_ids_json, last_search_time, search_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, query, images_json, sent_ids_json, datetime.now(), 1))
            
            conn.commit()
            conn.close()
            
            logging.info(f"💾 ✅ Persisted to database for user {user_id}")
        except Exception as e:
            logging.error(f"❌ Error saving to database: {e}")
    
    def get_unsent_images(self, user_id: str, count: int = 5) -> Optional[List[Dict]]:
        """
        Lấy ảnh chưa gửi từ lần tìm kiếm cuối cùng
        First tries in-memory, then falls back to database if not in memory
        
        Args:
            user_id: ID người dùng
            count: Số lượng ảnh muốn lấy
            
        Returns:
            Danh sách ảnh chưa gửi, hoặc None nếu không có
        """
        # Try to load from memory first
        if user_id not in self.memory:
            # Try to load from database
            self._load_from_database(user_id)
        
        if user_id not in self.memory:
            logging.warning(f"⚠️ No search history for user {user_id} (not in memory or database)")
            return None
        
        data = self.memory[user_id]
        images = data['images']
        sent_ids = data['sent_image_ids']
        
        # Lấy ảnh chưa gửi
        unsent = [img for img in images if img.get('id') not in sent_ids]
        
        if not unsent:
            logging.warning(f"⚠️ No unsent images for user {user_id}")
            return None
        
        # Lấy 'count' ảnh đầu tiên và mark là đã gửi
        result = unsent[:count]
        for img in result:
            sent_ids.add(img.get('id'))
        
        # Save updated sent_ids to database
        self._update_sent_ids_in_database(user_id, sent_ids)
        
        logging.info(f"📤 Retrieved {len(result)} unsent images for user {user_id}")
        return result
    
    def mark_image_as_sent(self, user_id: str, image_id: str):
        """Mark ảnh đã gửi"""
        if user_id in self.memory:
            self.memory[user_id]['sent_image_ids'].add(image_id)
            # Update database
            self._update_sent_ids_in_database(user_id, self.memory[user_id]['sent_image_ids'])
    
    def get_last_query(self, user_id: str) -> Optional[str]:
        """
        Lấy query tìm kiếm cuối cùng của user
        First tries in-memory, then falls back to database if not in memory
        """
        # Try to load from memory first
        if user_id not in self.memory:
            # Try to load from database
            self._load_from_database(user_id)
        
        if user_id in self.memory:
            return self.memory[user_id]['query']
        return None
    
    def has_unsent_images(self, user_id: str) -> bool:
        """
        Check xem có ảnh chưa gửi không
        First tries in-memory, then falls back to database if not in memory
        """
        # Try to load from memory first
        if user_id not in self.memory:
            # Try to load from database
            self._load_from_database(user_id)
        
        if user_id not in self.memory:
            return False
        
        data = self.memory[user_id]
        images = data['images']
        sent_ids = data['sent_image_ids']
        unsent_count = len([img for img in images if img.get('id') not in sent_ids])
        
        return unsent_count > 0
    
    def _load_from_database(self, user_id: str):
        """
        Load search history from database into memory
        Used when in-memory cache is empty but database has data
        """
        try:
            conn = self._get_db_connection()
            if not conn:
                logging.warning("⚠️ Could not load from database (connection failed)")
                return
            
            cursor = conn.cursor()
            cursor.execute('''
                SELECT query, images_json, sent_image_ids_json, last_search_time, search_count
                FROM image_search_history
                WHERE user_id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                logging.info(f"ℹ️ No search history in database for user {user_id}")
                return
            
            # Deserialize from JSON
            query = row[0]
            images = json.loads(row[1])
            sent_ids = json.loads(row[2])
            last_search_time = row[3]
            search_count = row[4]
            
            # Load into memory
            self.memory[user_id] = {
                'query': query,
                'images': images,
                'sent_image_ids': set(sent_ids),  # Convert back to set
                'last_search_time': datetime.fromisoformat(last_search_time) if isinstance(last_search_time, str) else last_search_time,
                'search_count': search_count
            }
            
            logging.info(f"📖 Loaded search history from database for user {user_id}: '{query}' ({len(images)} images, {len(sent_ids)} sent)")
        
        except Exception as e:
            logging.error(f"❌ Error loading from database: {e}")
    
    def _update_sent_ids_in_database(self, user_id: str, sent_ids: set):
        """Update sent_image_ids in database"""
        try:
            conn = self._get_db_connection()
            if not conn:
                logging.warning("⚠️ Could not update database (connection failed)")
                return
            
            cursor = conn.cursor()
            sent_ids_json = json.dumps(list(sent_ids), ensure_ascii=False)
            
            cursor.execute('''
                UPDATE image_search_history
                SET sent_image_ids_json = ?
                WHERE user_id = ?
            ''', (sent_ids_json, user_id))
            
            conn.commit()
            conn.close()
            
            logging.info(f"📝 Updated sent_ids in database for user {user_id}")
        except Exception as e:
            logging.error(f"❌ Error updating database: {e}")
    
    def clear_user_memory(self, user_id: str):
        """Xóa memory của user (but keep in database)"""
        if user_id in self.memory:
            del self.memory[user_id]
            logging.info(f"🧹 Cleared image search memory for user {user_id}")


class AlternativeImageRequestDetector:
    """
    Phát hiện các request loại "ảnh khác", "ảnh tiếp theo", v.v.
    """
    
    def __init__(self):
        """Khởi tạo detector"""
        self.alternative_request_patterns = [
            # Tiếng Việt
            'ảnh khác', 'anh khac',
            'ảnh tiếp theo', 'anh tiep theo',
            'ảnh khác đi', 'anh khac di',
            'cho ảnh khác', 'cho anh khac',
            'tìm ảnh khác', 'tim anh khac',
            'ảnh nữa', 'anh nua',
            'ảnh khác tí', 'anh khac ti',
            'thêm ảnh', 'them anh',
            'ảnh tiếp', 'anh tiep',
            'cái khác', 'cai khac',
            'cái khác nữa', 'cai khac nua',
            
            # English
            'different image', 'another image', 'other image',
            'next image', 'more images', 'more photos',
            'different photo', 'other photo',
            'show me different',
        ]
    
    def is_alternative_request(self, message: str) -> bool:
        """
        Check xem message có phải request ảnh khác không
        
        Args:
            message: Tin nhắn từ người dùng
            
        Returns:
            True nếu là request ảnh khác
        """
        message_lower = message.lower()
        
        for pattern in self.alternative_request_patterns:
            if pattern in message_lower:
                logging.info(f"🔄 Alternative image request detected: '{pattern}' in '{message}'")
                return True
        
        return False
    
    def is_same_category_request(self, message: str) -> bool:
        """
        Check xem message có tìm kiếm lại ảnh cùng loại không
        Ví dụ: "tìm ảnh bò khác" → muốn tìm ảnh bò nhưng khác
        """
        message_lower = message.lower()
        
        # Patterns như "khác", "lại", "nữa" kèm với từ khóa
        patterns = [
            ('khác', ['bò', 'bo', 'heo', 'gà', 'ga', 'lúa', 'lua', 'ngô', 'ngo']),
            ('lại', ['ảnh', 'anh', 'hình', 'hinh']),
            ('nữa', ['ảnh', 'anh', 'hình', 'hinh']),
        ]
        
        for keyword, targets in patterns:
            if keyword in message_lower:
                for target in targets:
                    if target in message_lower:
                        logging.info(f"🔄 Same category request detected: '{keyword}' + '{target}'")
                        return True
        
        return False


# Khởi tạo singleton instances
image_search_memory = ImageSearchMemory()
alternative_detector = AlternativeImageRequestDetector()


def save_search_result(user_id: str, query: str, images: List[Dict]):
    """Helper - lưu kết quả tìm kiếm ảnh (to both memory and database)"""
    image_search_memory.save_search_result(user_id, query, images)


def get_unsent_images(user_id: str, count: int = 5) -> Optional[List[Dict]]:
    """Helper - lấy ảnh chưa gửi (loads from database if needed)"""
    return image_search_memory.get_unsent_images(user_id, count)


def get_last_query(user_id: str) -> Optional[str]:
    """Helper - lấy query cuối cùng (loads from database if needed)"""
    return image_search_memory.get_last_query(user_id)


def has_unsent_images(user_id: str) -> bool:
    """Helper - check có ảnh chưa gửi (loads from database if needed)"""
    return image_search_memory.has_unsent_images(user_id)


def is_alternative_request(message: str) -> bool:
    """Helper - detect request ảnh khác"""
    return alternative_detector.is_alternative_request(message)


def is_same_category_request(message: str) -> bool:
    """Helper - detect request ảnh cùng loại"""
    return alternative_detector.is_same_category_request(message)
