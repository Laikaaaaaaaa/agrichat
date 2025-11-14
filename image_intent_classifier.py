"""
Image Intent Classifier - ML-based approach
Sử dụng machine learning để phát hiện yêu cầu hình ảnh với độ chính xác cao
"""

import logging
import pickle
import os
from typing import Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline


class ImageIntentClassifier:
    """
    Classifier để phát hiện yêu cầu hình ảnh sử dụng ML
    Được huấn luyện trên các ví dụ yêu cầu ảnh thực tế
    """
    
    def __init__(self, model_path: str = None):
        """
        Khởi tạo classifier
        
        Args:
            model_path: Đường dẫn đến model đã lưu (nếu có)
        """
        self.model_path = model_path or os.path.join(
            os.path.dirname(__file__), 
            'models', 
            'image_intent_classifier.pkl'
        )
        self.model = None
        self.vectorizer = None
        self.classifier = None
        self.trained = False
        
        # Nếu model tồn tại, load nó
        if os.path.exists(self.model_path):
            self._load_model()
        else:
            self._init_default_model()
    
    def _init_default_model(self):
        """Khởi tạo model mặc định với training data"""
        # Training data: (message, label) - 1 = image request, 0 = not image request
        training_data = [
            # Image requests - positive examples
            ("tìm ảnh con bò", 1),
            ("cho tôi hình ảnh về con bò", 1),
            ("show me pictures of rice", 1),
            ("xem biểu đồ lúa", 1),
            ("lấy hình về nông nghiệp", 1),
            ("tìm ảnh của lúa", 1),
            ("cho tôi xem hình ngô", 1),
            ("hiển thị ảnh cà chua", 1),
            ("get images of vegetables", 1),
            ("find pictures of livestock", 1),
            ("show me cattle images", 1),
            ("tìm hình ảnh con heo", 1),
            ("xem ảnh gà", 1),
            ("cho tôi ảnh về nuôi trồng", 1),
            ("cần hình ảnh về nông sản", 1),
            ("tìm ảnh về chăn nuôi", 1),
            ("xem hình con trâu", 1),
            ("show photos of farming", 1),
            ("find images of agriculture", 1),
            ("lấy ảnh nông nghiệp", 1),
            ("tìm hình ảnh về nuôi cá", 1),
            ("cho xem ảnh tôm", 1),
            ("tìm ảnh về đất nông nghiệp", 1),
            ("xem ảnh phân bò", 1),
            ("hiển thị hình ảnh máy nông nghiệp", 1),
            ("tìm ảnh về phân bón", 1),
            ("show me equipment images", 1),
            ("xem hình về mô hình canh tác", 1),
            ("tìm ảnh về kỹ thuật trồng trọt", 1),
            
            # Non-image requests - negative examples
            ("bò ăn gì", 0),
            ("lúa trồng như thế nào", 0),
            ("ngô lúa khác gì nhau", 0),
            ("mùa nào trồng rau", 0),
            ("đất nông nghiệp cần gì", 0),
            ("chăn nuôi bò có lợi không", 0),
            ("cách nuôi tôm hiệu quả", 0),
            ("how to grow rice", 0),
            ("what do cows eat", 0),
            ("cà chua bị bệnh gì", 0),
            ("xử lý đất trước khi trồng", 0),
            ("phân bón nào tốt cho lúa", 0),
            ("khoảng cách trồng ngô bao nhiêu", 0),
            ("nước tưới nên bao nhiêu lần", 0),
            ("sâu bệnh trên lúa là gì", 0),
            ("bò ăn cỏ bao nhiêu mỗi ngày", 0),
            ("nuôi gà trên sân thượng được không", 0),
            ("tôm cần nước mặn hay ngọt", 0),
            ("cá chép sinh sản vào mùa nào", 0),
            ("canh tác hiện đại là gì", 0),
            ("muốn trồng lúa hữu cơ thì sao", 0),
            ("thuốc trừ sâu nào an toàn", 0),
            ("mô hình nuôi trồng kết hợp có lợi gì", 0),
            ("đây là loài cây gì", 0),
            ("tính toán năng suất cây trồng", 0),
            ("phương pháp bảo quản nông sản", 0),
        ]
        
        # Tách messages và labels
        messages = [msg for msg, _ in training_data]
        labels = [label for _, label in training_data]
        
        # Tạo pipeline: TfidfVectorizer + Naive Bayes
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=200,
                ngram_range=(1, 2),  # Unigrams and bigrams
                min_df=1,
                max_df=1.0,
                lowercase=True,
                token_pattern=r'(?u)\b\w+\b'
            )),
            ('classifier', MultinomialNB(alpha=0.1))
        ])
        
        # Huấn luyện model
        logging.info("🤖 Training image intent classifier...")
        self.model.fit(messages, labels)
        self.trained = True
        logging.info("✅ Model trained successfully")
        
        # Lưu model
        self._save_model()
    
    def _save_model(self):
        """Lưu model để dùng lại"""
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.model, f)
            logging.info(f"💾 Model saved to {self.model_path}")
        except Exception as e:
            logging.warning(f"⚠️ Could not save model: {e}")
    
    def _load_model(self):
        """Load model từ file"""
        try:
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            self.trained = True
            logging.info(f"📂 Model loaded from {self.model_path}")
        except Exception as e:
            logging.warning(f"⚠️ Could not load model: {e}")
            self._init_default_model()
    
    def predict(self, message: str) -> Tuple[bool, float]:
        """
        Dự đoán xem tin nhắn có phải yêu cầu ảnh không
        
        Args:
            message: Tin nhắn từ người dùng
            
        Returns:
            Tuple (is_image_request: bool, confidence: float 0-1)
        """
        if not self.model or not self.trained:
            logging.warning("⚠️ Model not trained, using default")
            return False, 0.5
        
        try:
            # Dự đoán
            prediction = self.model.predict([message])[0]
            
            # Lấy probability
            probabilities = self.model.predict_proba([message])[0]
            confidence = max(probabilities)  # Lấy xác suất cao nhất
            
            is_image_request = bool(prediction)
            
            logging.debug(f"🤖 Prediction: {is_image_request} (confidence: {confidence:.2f}) for: '{message}'")
            
            return is_image_request, float(confidence)
        
        except Exception as e:
            logging.error(f"❌ Prediction error: {e}")
            return False, 0.5
    
    def predict_batch(self, messages: list) -> list:
        """
        Dự đoán nhiều tin nhắn cùng lúc
        
        Args:
            messages: Danh sách tin nhắn
            
        Returns:
            Danh sách tuple (is_image_request, confidence)
        """
        results = []
        for msg in messages:
            result = self.predict(msg)
            results.append(result)
        return results
    
    def retrain(self, training_data: list):
        """
        Huấn luyện lại model với dữ liệu mới
        
        Args:
            training_data: Danh sách (message, label) tuples
        """
        if not training_data:
            logging.warning("⚠️ Empty training data")
            return
        
        messages = [msg for msg, _ in training_data]
        labels = [label for _, label in training_data]
        
        logging.info(f"🔄 Retraining model with {len(training_data)} examples...")
        self.model.fit(messages, labels)
        self.trained = True
        self._save_model()
        logging.info("✅ Model retrained and saved")


# Khởi tạo singleton instance
image_classifier = ImageIntentClassifier()


def is_image_request(message: str, threshold: float = 0.5) -> Tuple[bool, float]:
    """
    Hàm helper - kiểm tra yêu cầu ảnh bằng ML
    
    Args:
        message: Tin nhắn
        threshold: Ngưỡng confidence (0-1), mặc định 0.5
        
    Returns:
        (is_request, confidence)
    """
    is_request, confidence = image_classifier.predict(message)
    
    # Chỉ xem là image request nếu confidence >= threshold
    return is_request and confidence >= threshold, confidence


def get_classifier():
    """Lấy classifier instance"""
    return image_classifier
