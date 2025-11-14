"""
Image Search Memory Module
Quản lý lịch sử tìm kiếm ảnh để xử lý requests như "ảnh khác", "ảnh tiếp theo", etc.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime


class ImageSearchMemory:
    """
    Lưu trữ thông tin về lần tìm ảnh cuối cùng của user
    Để xử lý các request như "ảnh khác", "ảnh tiếp theo", etc.
    """
    
    def __init__(self):
        """Khởi tạo memory - per user"""
        # Format: {user_id: {
        #   'query': 'con bò',
        #   'images': [{'url': '...', 'id': '...', ...}, ...],
        #   'sent_image_ids': set(),  # IDs của ảnh đã gửi
        #   'last_search_time': datetime,
        #   'search_count': int
        # }}
        self.memory = {}
    
    def save_search_result(self, user_id: str, query: str, images: List[Dict]):
        """
        Lưu kết quả tìm kiếm ảnh
        
        Args:
            user_id: ID người dùng
            query: Query tìm kiếm (ví dụ: "con bò")
            images: Danh sách ảnh tìm được
        """
        if not user_id or not query or not images:
            return
        
        self.memory[user_id] = {
            'query': query,
            'images': images,
            'sent_image_ids': set(),  # Chưa gửi ảnh nào
            'last_search_time': datetime.now(),
            'search_count': 1
        }
        
        logging.info(f"💾 Saved image search result for user {user_id}: '{query}' ({len(images)} images)")
    
    def get_unsent_images(self, user_id: str, count: int = 5) -> Optional[List[Dict]]:
        """
        Lấy ảnh chưa gửi từ lần tìm kiếm cuối cùng
        
        Args:
            user_id: ID người dùng
            count: Số lượng ảnh muốn lấy
            
        Returns:
            Danh sách ảnh chưa gửi, hoặc None nếu không có
        """
        if user_id not in self.memory:
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
        
        logging.info(f"📤 Retrieved {len(result)} unsent images for user {user_id}")
        return result
    
    def mark_image_as_sent(self, user_id: str, image_id: str):
        """Mark ảnh đã gửi"""
        if user_id in self.memory:
            self.memory[user_id]['sent_image_ids'].add(image_id)
    
    def get_last_query(self, user_id: str) -> Optional[str]:
        """Lấy query tìm kiếm cuối cùng của user"""
        if user_id in self.memory:
            return self.memory[user_id]['query']
        return None
    
    def has_unsent_images(self, user_id: str) -> bool:
        """Check xem có ảnh chưa gửi không"""
        if user_id not in self.memory:
            return False
        
        data = self.memory[user_id]
        images = data['images']
        sent_ids = data['sent_image_ids']
        unsent_count = len([img for img in images if img.get('id') not in sent_ids])
        
        return unsent_count > 0
    
    def clear_user_memory(self, user_id: str):
        """Xóa memory của user"""
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
    """Helper - lưu kết quả tìm kiếm ảnh"""
    image_search_memory.save_search_result(user_id, query, images)


def get_unsent_images(user_id: str, count: int = 5) -> Optional[List[Dict]]:
    """Helper - lấy ảnh chưa gửi"""
    return image_search_memory.get_unsent_images(user_id, count)


def get_last_query(user_id: str) -> Optional[str]:
    """Helper - lấy query cuối cùng"""
    return image_search_memory.get_last_query(user_id)


def has_unsent_images(user_id: str) -> bool:
    """Helper - check có ảnh chưa gửi"""
    return image_search_memory.has_unsent_images(user_id)


def is_alternative_request(message: str) -> bool:
    """Helper - detect request ảnh khác"""
    return alternative_detector.is_alternative_request(message)


def is_same_category_request(message: str) -> bool:
    """Helper - detect request ảnh cùng loại"""
    return alternative_detector.is_same_category_request(message)
