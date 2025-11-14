"""
Image Request Handler Module
Xử lý tất cả các tin nhắn yêu cầu ảnh từ người dùng
"""

import logging
import re
from typing import Tuple, Optional, List, Dict
from image_intent_classifier import image_classifier


class ImageRequestHandler:
    """Xử lý phát hiện và trích xuất yêu cầu ảnh từ tin nhắn"""
    
    def __init__(self):
        """Khởi tạo handler với các từ khóa và pattern"""
        
        # Từ khóa ảnh trực tiếp
        self.image_keywords = [
            'hình ảnh', 'ảnh', 'xem ảnh', 'xem hình', 'coi ảnh', 'coi hình',
            'cho tôi xem', 'cho tôi xem hình', 'cho tôi coi ảnh', 'cho tôi coi hình',
            'đưa ảnh', 'hiển thị ảnh', 'cho xin ảnh', 'cho xin hình',
            'tìm ảnh', 'tìm hình', 'kiếm ảnh', 'kiếm hình',
            'lấy ảnh', 'lấy hình', 'gửi ảnh', 'gửi hình',
            'show', 'image', 'picture', 'photo',
            'cho tôi ảnh', 'cho tôi hình', 'đưa tôi ảnh', 'đưa tôi hình',
            'muốn xem ảnh', 'muốn xem hình', 'cần ảnh', 'cần hình',
            'tim anh', 'tim hinh', 'cho toi anh', 'cho toi hinh',  # No diacritics
        ]
        
        # Từ khóa nông nghiệp + gia súc
        self.livestock_keywords = [
            'số lượng gia súc', 'tỷ lệ gia súc', 'phân bố gia súc',
            'số lượng bò', 'số lượng heo', 'số lượng gà',
            'thống kê nông nghiệp', 'dữ liệu chăn nuôi',
            'livestock data', 'agricultural statistics',
            'so luong gia suc', 'so luong bo',  # No diacritics
        ]
        
        # Action words cho pattern matching
        self.action_words = [
            'tìm', 'tim', 'show', 'hiển thị', 'hien thi', 'get', 'lấy', 'lay',
            'xem', 'coi', 'cho', 'xin', 'vui lòng', 'vui long',
            'làm ơn', 'lam on', 'please', 'find', 'search', 'look for',
            'display', 'provide', 'send me', 'give me',
        ]
        
        # Image objects
        self.image_objects = [
            'ảnh', 'anh', 'hình', 'hinh', 'photo', 'image', 'picture',
            'biểu đồ', 'bieu do', 'đồ thị', 'do thi', 'chart', 'graph',
            'hình ảnh', 'hinh anh',
        ]

    def is_image_request(self, message: str, use_ml: bool = True) -> bool:
        """
        Kiểm tra xem tin nhắn có phải là yêu cầu ảnh không
        
        Args:
            message: Tin nhắn từ người dùng
            use_ml: Sử dụng ML classifier (True) hay rule-based (False)
            
        Returns:
            True nếu là yêu cầu ảnh, False nếu không
        """
        if not message or not isinstance(message, str):
            return False
        
        # STEP 1: Sử dụng ML Classifier (chính xác hơn)
        if use_ml:
            try:
                is_request, confidence = image_classifier.predict(message)
                logging.info(f"🤖 ML prediction: {is_request} (confidence: {confidence:.2%}) for: '{message}'")
                if confidence > 0.5:  # Lowered threshold from 0.6 to 0.5
                    return is_request
                else:
                    logging.info(f"⚠️ Confidence {confidence:.2%} below threshold 50%, falling back to rule-based")
            except Exception as e:
                logging.warning(f"⚠️ ML prediction failed: {e}, falling back to rule-based")
        
        # STEP 2: Fallback - Rule-based detection
        result = self._rule_based_detection(message)
        logging.info(f"📋 Rule-based detection result: {result} for: '{message}'")
        return result
    
    def _rule_based_detection(self, message: str) -> bool:
        """
        Rule-based fallback detection (nếu ML thất bại)
        """
        message_lower = message.lower()
        
        # STEP 1: Kiểm tra hard keywords
        all_keywords = (
            self.image_keywords + self.livestock_keywords
        )
        
        for keyword in all_keywords:
            if keyword in message_lower:
                logging.debug(f"🖼️ Found hard keyword '{keyword}' in message")
                return True
        
        # STEP 2: Action + Object pattern matching
        has_action = any(action in message_lower for action in self.action_words)
        has_image_object = any(obj in message_lower for obj in self.image_objects)
        
        if has_action and has_image_object:
            logging.debug(f"🖼️ Detected image intent via action+object pattern")
            return True
        
        return False

    def extract_query(self, message: str, is_image_request: bool = True) -> str:
        """
        Trích xuất query tìm kiếm từ tin nhắn yêu cầu ảnh
        
        Args:
            message: Tin nhắn từ người dùng
            is_image_request: Đã được xác nhận là yêu cầu ảnh
            
        Returns:
            Query sạch để tìm kiếm ảnh
        """
        if not message:
            return 'nông nghiệp'
        
        message_lower = message.lower()
        query = message
        
        # Xóa tất cả các keyword của ảnh ra khỏi tin nhắn
        all_keywords = (
            self.image_keywords + self.livestock_keywords
        )
        
        for keyword in sorted(all_keywords, key=len, reverse=True):  # Xóa keyword dài trước
            query = query.lower().replace(keyword, ' ').strip()
        
        # Stop words để bỏ bớt
        stop_words = [
            'của', 'cho', 'về', 'với', 'trong', 'tôi', 'mình', 'bạn', 'đi',
            'nha', 'ạ', 'nhé', 'được', 'là', 'và', 'hay', 'hoặc', 'thì',
            'va', 'hay', 'hoac', 'toi', 'ban', 'duoc',  # No diacritics
        ]
        
        # Tách từ và lọc stop words
        query_words = [
            word for word in query.split()
            if word and word not in stop_words and len(word) > 1
        ]
        
        clean_query = ' '.join(query_words).strip()
        
        # Fallback nếu query rỗng
        if not clean_query or len(clean_query) < 2:
            clean_query = 'nông nghiệp'
        
        logging.info(f"🎯 Extracted search query: '{clean_query}' from message: '{message}'")
        return clean_query

    def get_response_message(self, query: str, image_count: int) -> str:
        """
        Tạo tin nhắn phản hồi khi tìm được ảnh
        
        Args:
            query: Query tìm kiếm
            image_count: Số lượng ảnh tìm được
            
        Returns:
            Tin nhắn phản hồi
        """
        if image_count > 0:
            return f"🖼️ Đây là {image_count} ảnh về '{query}':"
        else:
            return f"😔 Xin lỗi, tôi không tìm được ảnh nào về '{query}'. Bạn thử từ khóa khác nhé!"

    def classify_request_type(self, message: str) -> str:
        """
        Phân loại loại yêu cầu ảnh: livestock hoặc general
        
        Args:
            message: Tin nhắn từ người dùng
            
        Returns:
            Loại yêu cầu: 'livestock' hoặc 'general'
        """
        message_lower = message.lower()
        
        # Kiểm tra từng loại
        if any(kw in message_lower for kw in self.livestock_keywords):
            return 'livestock'
        else:
            return 'general'

    def extract_subjects(self, message: str) -> List[str]:
        """
        Trích xuất các chủ đề chính từ tin nhắn (ngoài từ khóa yêu cầu ảnh)
        
        Args:
            message: Tin nhắn từ người dùng
            
        Returns:
            Danh sách các chủ đề
        """
        subjects = []
        
        # Các pattern chủ đề nông nghiệp phổ biến
        agriculture_patterns = {
            'lúa': ['lúa', 'lua', 'rice'],
            'ngô': ['ngô', 'ngo', 'corn'],
            'cà chua': ['cà chua', 'ca chua', 'tomato'],
            'xà lách': ['xà lách', 'xa lach', 'lettuce'],
            'bò': ['bò', 'bo', 'cattle', 'cow'],
            'heo': ['heo', 'pig', 'pork'],
            'gà': ['gà', 'ga', 'chicken'],
            'vịt': ['vịt', 'vit', 'duck'],
            'tôm': ['tôm', 'tom', 'shrimp'],
            'cá': ['cá', 'ca', 'fish'],
        }
        
        message_lower = message.lower()
        
        for subject, patterns in agriculture_patterns.items():
            for pattern in patterns:
                if pattern in message_lower:
                    subjects.append(subject)
                    break  # Tránh duplicate
        
        return list(set(subjects))  # Remove duplicates

    def build_search_context(self, message: str) -> Dict[str, any]:
        """
        Xây dựng context đầy đủ cho tìm kiếm ảnh
        
        Args:
            message: Tin nhắn từ người dùng
            
        Returns:
            Dictionary chứa đầy đủ thông tin về yêu cầu
        """
        is_image_req = self.is_image_request(message)
        
        return {
            'is_image_request': is_image_req,
            'request_type': self.classify_request_type(message) if is_image_req else None,
            'query': self.extract_query(message) if is_image_req else None,
            'subjects': self.extract_subjects(message),
            'original_message': message,
            'message_lower': message.lower(),
        }


# Khởi tạo singleton instance
image_handler = ImageRequestHandler()


def is_image_request(message: str) -> bool:
    """Hàm helper - kiểm tra yêu cầu ảnh"""
    return image_handler.is_image_request(message)


def extract_query(message: str) -> str:
    """Hàm helper - trích xuất query"""
    return image_handler.extract_query(message)


def get_response_message(query: str, image_count: int) -> str:
    """Hàm helper - tạo tin nhắn phản hồi"""
    return image_handler.get_response_message(query, image_count)


def build_search_context(message: str) -> Dict[str, any]:
    """Hàm helper - xây dựng search context"""
    return image_handler.build_search_context(message)
