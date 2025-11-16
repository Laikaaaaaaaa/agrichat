"""
News Category Classifier using ML
Classifies articles into: Farming, Livestock, Technology, Weather, Market, Other
"""

import json
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import pickle
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Category keywords for rule-based fallback
CATEGORY_KEYWORDS = {
    'chăn_nuôi': [
        'chăn nuôi', 'gia súc', 'gia cầm', 'đàn vật nuôi', 'vật nuôi', 'bò', 'lợn', 'gà', 'vịt', 'cá', 
        'tôm', 'nuôi trồng', 'thức ăn chăn nuôi', 'vaccine gia súc', 'bệnh gia súc', 'sản xuất chăn nuôi',
        'chất lượng thịt', 'sữa', 'trứng', 'bảo vệ vật nuôi', 'cải thiện chăn nuôi', 'kỹ thuật chăn nuôi',
        'trang trại chăn nuôi', 'nuôi dưỡng gia súc', 'giống gia súc'
    ],
    'nông_nghiệp': [
        'nông nghiệp', 'cây trồng', 'lúa', 'ngô', 'khoai', 'rau', 'quả', 'hoa', 'cacao', 'cà phê',
        'trồng trọt', 'giống cây', 'phân bón', 'phòng trừ sâu bệnh', 'máy nông nghiệp', 'tưới tiêu',
        'đất nông nghiệp', 'canh tác', 'vụ mưa', 'vụ khô', 'thu hoạch', 'gieo trồng', 'nông dân',
        'sản lượng lúa', 'cải thiện năng suất', 'kỹ thuật canh tác', 'trang trại trồng trọt'
    ],
    'công_nghệ': [
        'công nghệ', 'AI', 'máy tính', 'ứng dụng', 'phần mềm', 'robot', 'IoT', 'công nghệ nông nghiệp',
        'nông nghiệp 4.0', 'tự động hóa', 'trí tuệ nhân tạo', 'machine learning', 'smart farm',
        'cảm biến', 'dữ liệu', 'blockchain', 'công nghệ sinh học', 'phân tích dữ liệu nông nghiệp',
        'ứng dụng công nghệ', 'hệ thống thông minh'
    ],
    'thời_tiết': [
        'thời tiết', 'mưa', 'nắng', 'gió', 'dự báo', 'bão', 'lũ', 'hạn hán', 'nhiệt độ', 'độ ẩm',
        'khí hậu', 'thay đổi khí hậu', 'biến đổi khí hậu', 'thời tiết nông nghiệp', 'cảnh báo thời tiết',
        'dự báo mưa', 'dự báo nắng', 'điều kiện thời tiết'
    ],
    'thị_trường': [
        'thị trường', 'giá', 'buôn bán', 'xuất khẩu', 'nhập khẩu', 'cung cầu', 'kinh tế', 'lợi nhuận',
        'chi phí', 'tăng giá', 'giảm giá', 'doanh số', 'bán hàng', 'thương mại nông sản', 'nông sản',
        'giá nông sản', 'thị giá', 'khoá hàng', 'mua bán'
    ],
    'chính_sách': [
        'chính sách', 'pháp luật', 'hỗ trợ', 'chương trình', 'dự án', 'quyết định', 'điều lệ',
        'hướng dẫn', 'quy định', 'yêu cầu', 'tiêu chuẩn', 'hợp tác', 'hội nhập', 'nghị định',
        'luật lệ', 'công bố', 'thông tư', 'cải cách', 'phát triển xanh', 'phát thải', 'khí hậu',
        'tái cơ cấu', 'số hóa', 'quản trị'
    ]
}

# Keywords to exclude or reduce weight for policy/regulation classification
POLICY_INDICATORS = [
    'nghị định', 'luật', 'quy định', 'thông tư', 'quyết định', 'công bố', 'cải cách',
    'phát thải', 'phát triển xanh', 'tái cơ cấu', 'số hóa quản trị', 'thể chế'
]

# Keywords to EXCLUDE - common false positives
EXCLUSION_KEYWORDS = {
    'chăn_nuôi': ['nông nghiệp chung', 'nông nghiệp môi trường', 'tái cơ cấu nông nghiệp', 'phát triển nông nghiệp'],
    'nông_nghiệp': ['chăn nuôi gia súc', 'nuôi vật nuôi', 'thức ăn chăn nuôi'],
}

class NewsClassifier:
    """
    ML-based news classifier for agricultural articles
    """
    
    MODEL_PATH = 'news_classifier_model.pkl'
    
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.categories = list(CATEGORY_KEYWORDS.keys())
        self.load_or_create_model()
    
    def create_training_data(self):
        """Create training data from keywords"""
        X_train = []
        y_train = []
        
        # Create synthetic training data from keywords
        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                # Create variations of keyword examples
                X_train.append(keyword)
                y_train.append(category)
                
                # Add some phrase variations
                if len(keyword.split()) == 1:
                    X_train.append(f"bài viết về {keyword}")
                    y_train.append(category)
                    X_train.append(f"tin tức {keyword}")
                    y_train.append(category)
        
        return X_train, y_train
    
    def train_model(self):
        """Train the ML model"""
        try:
            logger.info('🤖 Training news classifier model...')
            
            X_train, y_train = self.create_training_data()
            
            # Create pipeline with TfidfVectorizer and MultinomialNB
            self.model = Pipeline([
                ('tfidf', TfidfVectorizer(
                    max_features=1000,
                    ngram_range=(1, 2),
                    min_df=1,
                    max_df=0.9
                )),
                ('clf', MultinomialNB())
            ])
            
            # Train model
            self.model.fit(X_train, y_train)
            
            # Save model
            self.save_model()
            logger.info('✅ Model trained and saved successfully')
            
        except Exception as e:
            logger.error(f"❌ Error training model: {e}")
    
    def save_model(self):
        """Save trained model to file"""
        try:
            with open(self.MODEL_PATH, 'wb') as f:
                pickle.dump(self.model, f)
            logger.info(f'💾 Model saved to {self.MODEL_PATH}')
        except Exception as e:
            logger.error(f"❌ Error saving model: {e}")
    
    def load_or_create_model(self):
        """Load existing model or create new one"""
        if os.path.exists(self.MODEL_PATH):
            try:
                with open(self.MODEL_PATH, 'rb') as f:
                    self.model = pickle.load(f)
                logger.info('✅ Model loaded from disk')
                return
            except Exception as e:
                logger.warning(f"⚠️ Error loading model: {e}")
        
        # Create new model if not found
        self.train_model()
    
    def _extract_ml_features(self, title, description, content):
        """Extract and combine features for ML prediction"""
        # Combine all text fields with importance weighting
        features = []
        
        # Title has highest importance (2x weight)
        if title:
            features.append(title + ' ' + title)
        
        # Description has medium importance (1.5x weight)
        if description:
            features.append(description + ' ' + description[:len(description)//2])
        
        # Content has normal weight
        if content:
            # Take first 500 chars of content
            features.append(content[:500])
        
        combined = ' '.join(features).lower()
        return combined
    
    def _rule_based_classification(self, title, description, content):
        """
        Improved rule-based classification with:
        - Policy detection (high priority)
        - Exclusion rules to prevent false positives
        - Content analysis (not just keyword matching)
        - Weighted scoring
        """
        combined_text = (title + ' ' + description + ' ' + content[:500]).lower()
        
        # Check for policy-related content first (high priority)
        policy_score = sum(1 for indicator in POLICY_INDICATORS if indicator in combined_text)
        if policy_score >= 2:
            logger.info("📋 Detected as POLICY based on policy indicators")
            return 'chính_sách', 0.9
        
        # Check for exclusions that would indicate another category
        for category, exclusions in EXCLUSION_KEYWORDS.items():
            for exclusion in exclusions:
                if exclusion in combined_text:
                    logger.info(f"❌ Exclusion match: '{exclusion}' → NOT {category}")
        
        # Calculate scores for each category
        category_scores = {}
        
        for category, keywords in CATEGORY_KEYWORDS.items():
            score = 0
            matches = []
            
            for keyword in keywords:
                keyword_lower = keyword.lower()
                # Exact phrase match (higher weight)
                if keyword_lower in combined_text:
                    # Check if it's an exclusion
                    is_excluded = False
                    if category in EXCLUSION_KEYWORDS:
                        for exclusion in EXCLUSION_KEYWORDS[category]:
                            if exclusion in combined_text and keyword_lower not in exclusion:
                                is_excluded = True
                                break
                    
                    if not is_excluded:
                        score += 2  # Higher weight for exact matches
                        matches.append(keyword)
                # Partial word match (lower weight)
                elif any(word in combined_text for word in keyword_lower.split()):
                    score += 0.5
            
            if matches:
                logger.info(f"  {category}: score={score}, matches={matches[:3]}")
            
            category_scores[category] = score
        
        # Get category with highest score
        if category_scores and max(category_scores.values()) > 0:
            best_category = max(category_scores, key=category_scores.get)
            score = category_scores[best_category]
            
            # Normalize confidence to 0-1
            # Score of 2 = one exact match = 0.5 confidence
            # Score of 4+ = high confidence
            confidence = min(score / 4.0, 1.0)
            
            logger.info(f"📋 Rule-based result: {best_category} (score={score}, confidence={confidence:.2f})")
            return best_category, confidence
        
        logger.info("📋 No category matched, returning 'khác'")
        return 'khác', 0.0
    
    def classify(self, article=None, title='', description='', content=''):
        """
        Classify article into category
        Uses ML prediction with rule-based verification
        Can accept either:
        - article dict with 'title', 'description', 'source', 'content'
        - individual title, description, content parameters
        """
        try:
            # Handle both dict and parameter inputs
            if isinstance(article, dict):
                title = article.get('title', '')
                description = article.get('description', '')
                source = article.get('source', '')
                content = article.get('content', '')
                # Combine source into description for better context
                if source:
                    description = f"{source} {description}" if description else source
            
            # Ensure all values are strings
            title = str(title or '')
            description = str(description or '')
            content = str(content or '')
            
            # Prepare features
            combined_text = self._extract_ml_features(title, description, content)
            
            # Get ML prediction
            ml_prediction = None
            ml_confidence = 0.0
            
            if self.model and combined_text.strip():
                try:
                    predicted_category = self.model.predict([combined_text])[0]
                    probabilities = self.model.predict_proba([combined_text])[0]
                    ml_confidence = float(max(probabilities))
                    ml_prediction = predicted_category
                    
                    logger.info(f"🤖 ML Prediction: {predicted_category} (confidence: {ml_confidence:.2f})")
                except Exception as e:
                    logger.warning(f"⚠️ ML prediction error: {e}")
            
            # Get rule-based classification
            rule_category, rule_confidence = self._rule_based_classification(
                title, description, content
            )
            
            logger.info(f"📋 Rule-based: {rule_category} (confidence: {rule_confidence:.2f})")
            
            # Combine predictions: prefer ML if high confidence, else use rule-based
            if ml_confidence >= 0.4:
                final_category = ml_prediction
                final_confidence = ml_confidence
                method = 'ML'
            elif rule_confidence > 0:
                final_category = rule_category
                final_confidence = rule_confidence
                method = 'Rule-based'
            else:
                final_category = 'khác'
                final_confidence = 0.0
                method = 'Default'
            
            # Map internal category names to display names
            category_display = {
                'chăn_nuôi': 'Chăn nuôi',
                'nông_nghiệp': 'Nông nghiệp',
                'công_nghệ': 'Công nghệ',
                'thời_tiết': 'Thời tiết',
                'thị_trường': 'Thị trường',
                'chính_sách': 'Chính sách',
                'khác': 'Khác'
            }
            
            result = {
                'category': final_category,
                'display_category': category_display.get(final_category, final_category),
                'confidence': round(final_confidence, 2),
                'method': method,
                'ml_prediction': ml_prediction,
                'ml_confidence': round(ml_confidence, 2),
                'rule_prediction': rule_category,
                'rule_confidence': round(rule_confidence, 2)
            }
            
            logger.info(f"✅ Final classification: {result['display_category']} ({method}, {final_confidence:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"❌ Classification error: {e}")
            return {
                'category': 'khác',
                'display_category': 'Khác',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def classify_batch(self, articles):
        """
        Classify multiple articles
        articles: list of dicts with 'title', 'description', 'content'
        """
        results = []
        for article in articles:
            result = self.classify(
                title=article.get('title', ''),
                description=article.get('description', ''),
                content=article.get('content', '')
            )
            results.append({
                **article,
                'classification': result
            })
        
        return results


# Global classifier instance
_classifier = None

def get_classifier():
    """Get or create global classifier instance"""
    global _classifier
    if _classifier is None:
        _classifier = NewsClassifier()
    return _classifier

def classify_article(title='', description='', content=''):
    """
    Convenience function to classify a single article
    """
    classifier = get_classifier()
    return classifier.classify(title, description, content)

def classify_articles(articles):
    """
    Convenience function to classify multiple articles
    """
    classifier = get_classifier()
    return classifier.classify_batch(articles)
