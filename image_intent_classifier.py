"""
Image Intent Classifier - Advanced ML-based approach
Sử dụng ensemble learning để phát hiện yêu cầu hình ảnh với độ chính xác cao
"""

import logging
import pickle
import os
import unicodedata
from typing import Tuple
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import VotingClassifier, RandomForestClassifier
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.preprocessing import StandardScaler


class DiacriticsNormalizer:
    """Normalize Vietnamese text by removing diacritics"""
    
    @staticmethod
    def normalize(text):
        """Remove diacritics from Vietnamese text"""
        if not text:
            return text
        nfd = unicodedata.normalize('NFD', text)
        return ''.join(ch for ch in nfd if unicodedata.category(ch) != 'Mn')


class ImageIntentClassifier:
    """
    Advanced classifier để phát hiện yêu cầu hình ảnh sử dụng ensemble ML
    - Kết hợp Naive Bayes, Logistic Regression, và SVM
    - Hỗ trợ Vietnamese text normalization
    - Training data mở rộng với negative examples từ learning intent
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
            'image_intent_classifier_v2.pkl'
        )
        self.model = None
        self.vectorizer = None
        self.normalizer = DiacriticsNormalizer()
        self.trained = False
        
        # Nếu model tồn tại, load nó
        if os.path.exists(self.model_path):
            self._load_model()
        else:
            self._init_ensemble_model()
    
    def _preprocess_text(self, text: str) -> str:
        """
        Tiền xử lý text: lowercase, normalize diacritics
        """
        if not text:
            return text
        text = text.lower().strip()
        # Normalize Vietnamese diacritics
        text = self.normalizer.normalize(text)
        return text
    
    def _init_ensemble_model(self):
        """Khởi tạo ensemble model với multiple classifiers"""
        
        # ✅ EXPANDED Training data: nhiều positive + negative examples hơn
        training_data = [
            # === POSITIVE: Image requests ===
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
            ("ảnh con trâu đi", 1),
            ("hình về cà chua", 1),
            ("coi hình bệnh sâu ăn cây", 1),
            ("xem ảnh sâu bệnh lúa", 1),
            ("find rice disease images", 1),
            ("ảnh về thuốc trừ sâu", 1),
            ("hình minh họa nuôi cá", 1),
            ("show cattle breeding", 1),
            ("ảnh về lợn ăn cỏ", 1),
            ("hình về bò sữa", 1),
            ("tìm ảnh máy kéo", 1),
            ("hiển thị ảnh khoai tây", 1),
            ("ảnh về kỹ thuật canh tác", 1),
            ("tìm hình về giống lúa", 1),
            ("ảnh về vườn rau", 1),
            ("hình ảnh cây cà chua khỏe mạnh", 1),
            
            # === NEGATIVE: Learning/Understanding intent (NOT image requests) ===
            ("tìm hiểu về nông nghiệp", 0),
            ("tim hieu ve nong nghiep", 0),
            ("tôi muốn tìm hiểu về nông nghiệp", 0),
            ("tôi muốn tìm hiểu cách trồng lúa", 0),
            ("học về nuôi bò", 0),
            ("học cách trồng ngô", 0),
            ("tìm tòi về canh tác hiện đại", 0),
            ("khám phá kỹ thuật nông nghiệp", 0),
            ("tôi muốn hiểu biết về chăn nuôi", 0),
            ("giải thích cho tôi về cà chua", 0),
            ("hỏi về khoảng cách trồng lúa", 0),
            ("trao đổi về mô hình nuôi cá", 0),
            ("thảo luận về phân bón nào tốt", 0),
            ("bàn luận về sâu bệnh trên cây", 0),
            ("tôi muốn nói chuyện về nông sản", 0),
            
            # === NEGATIVE: Non-image questions ===
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
            ("heo nên ăn gì", 0),
            ("gà trống sản xuất trứng không", 0),
            ("cây cà chua cần bao nhiêu ánh sáng", 0),
            ("rau xà lách mọc bao lâu", 0),
            ("cách bảo quản khoai tây", 0),
            ("vườn rau nên trồng cây gì", 0),
        ]
        
        # Tiền xử lý training data
        preprocessed_data = [
            (self._preprocess_text(msg), label) for msg, label in training_data
        ]
        
        messages = [msg for msg, _ in preprocessed_data]
        labels = [label for _, label in preprocessed_data]
        
        # ✅ ENSEMBLE: Kết hợp nhiều feature extractors
        feature_union = FeatureUnion([
            # TF-IDF với unigrams + bigrams
            ('tfidf', TfidfVectorizer(
                max_features=300,
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.9,
                lowercase=True,
                token_pattern=r'(?u)\b\w+\b'
            )),
            # Count vectorizer cho character-level n-grams
            ('char_ngrams', TfidfVectorizer(
                max_features=200,
                analyzer='char',
                ngram_range=(2, 3),
                lowercase=True,
            )),
        ])
        
        # ✅ VOTING CLASSIFIER: Kết hợp 3 models
        self.model = VotingClassifier(
            estimators=[
                ('nb', Pipeline([
                    ('features', feature_union),
                    ('clf', MultinomialNB(alpha=0.5))
                ])),
                ('lr', Pipeline([
                    ('features', feature_union),
                    ('scaler', StandardScaler(with_mean=False)),
                    ('clf', LogisticRegression(max_iter=200, C=1.0, class_weight='balanced'))
                ])),
                ('svm', Pipeline([
                    ('features', feature_union),
                    ('scaler', StandardScaler(with_mean=False)),
                    ('clf', LinearSVC(max_iter=2000, C=1.0, class_weight='balanced', random_state=42))
                ]))
            ],
            voting='soft',
            weights=[1, 1.5, 1.5]  # Cho SVM và LR trọng số cao hơn
        )
        
        # Huấn luyện model
        logging.info(f"🤖 Training advanced ensemble image intent classifier with {len(training_data)} examples...")
        self.model.fit(messages, labels)
        self.trained = True
        logging.info("✅ Ensemble model trained successfully")
        
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
            logging.info(f"📂 Ensemble model loaded from {self.model_path}")
        except Exception as e:
            logging.warning(f"⚠️ Could not load model: {e}, retraining...")
            self._init_ensemble_model()
    
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
            # Tiền xử lý
            preprocessed = self._preprocess_text(message)
            
            # Dự đoán
            prediction = self.model.predict([preprocessed])[0]
            
            # Lấy probability
            probabilities = self.model.predict_proba([preprocessed])[0]
            confidence = max(probabilities)  # Lấy xác suất cao nhất
            
            is_image_request = bool(prediction)
            
            logging.debug(f"🤖 Ensemble prediction: {is_image_request} (confidence: {confidence:.2f}) for: '{message}'")
            
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
        
        preprocessed_data = [
            (self._preprocess_text(msg), label) for msg, label in training_data
        ]
        
        messages = [msg for msg, _ in preprocessed_data]
        labels = [label for _, label in preprocessed_data]
        
        logging.info(f"🔄 Retraining ensemble model with {len(training_data)} examples...")
        self.model.fit(messages, labels)
        self.trained = True
        self._save_model()
        logging.info("✅ Ensemble model retrained and saved")


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

