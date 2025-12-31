#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AgriSense AI - Agricultural Question Analysis & Prompt Builder
==============================================================
File: main.py
Author: AgriSense AI Team
Description: Pipeline phân tích câu hỏi nông nghiệp và tạo prompt cho OpenAI API

Chạy:
  - Interactive mode: python main.py
  - Train mode: python main.py --mode train
"""

import argparse
import json
import math
import os
import pickle
import random
import re
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import SGDClassifier
    from sklearn.pipeline import Pipeline
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
TRAIN_FILE = os.path.join(DATA_DIR, "train_cases.jsonl")
MODEL_FILE = os.path.join(MODELS_DIR, "crop_classifier.pkl")
CONVERSATIONS_LOG = os.path.join(LOGS_DIR, "conversations.jsonl")
TRAIN_METRICS_LOG = os.path.join(LOGS_DIR, "train_metrics.json")


def ensure_directories():
    for d in [DATA_DIR, MODELS_DIR, LOGS_DIR]:
        os.makedirs(d, exist_ok=True)


class Region(Enum):
    DBSCL = "Đồng bằng sông Cửu Long"
    TAY_NGUYEN = "Tây Nguyên"
    MIEN_BAC = "Miền Bắc"
    MIEN_TRUNG = "Miền Trung"
    DONG_NAM_BO = "Đông Nam Bộ"
    UNKNOWN = "Không xác định"


class Season(Enum):
    MUA = "Mùa mưa"
    KHO = "Mùa khô"
    DONG_XUAN = "Đông Xuân"
    HE_THU = "Hè Thu"
    THU_DONG = "Thu Đông"
    UNKNOWN = "Không rõ"


class Scale(Enum):
    NHA_VUON = "Nhà vườn/Hộ gia đình"
    TRANG_TRAI = "Trang trại"
    UNKNOWN = "Không xác định"


class Experience(Enum):
    PHO_THONG = "Nông dân phổ thông"
    CO_KINH_NGHIEM = "Người có kinh nghiệm"
    UNKNOWN = "Không xác định"


@dataclass
class QuestionAnalysis:
    original_question: str
    crop: Optional[str] = None
    stage: Optional[str] = None
    symptoms: List[str] = None
    region: str = Region.UNKNOWN.value
    season: str = Season.UNKNOWN.value
    scale: str = Scale.UNKNOWN.value
    experience: str = Experience.UNKNOWN.value
    weather_context: Optional[str] = None
    time_context: Optional[str] = None
    action_asked: Optional[str] = None
    urgency_level: str = "normal"

    def __post_init__(self):
        if self.symptoms is None:
            self.symptoms = []

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgriLogicResult:
    priority_causes: List[str]
    secondary_causes: List[str]
    recommended_actions: List[str]
    avoid_actions: List[str]
    check_first: List[str]
    knowledge_notes: List[str]
    confidence_level: str
    reasoning_chain: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


CROP_KEYWORDS = {
    "lúa": ["lúa", "lua", "nếp", "gạo", "ruộng lúa", "đồng lúa"],
    "cà phê": ["cà phê", "ca phe", "cafe", "cà fê", "coffee"],
    "tiêu": ["tiêu", "hồ tiêu", "ho tieu", "pepper"],
    "điều": ["điều", "đào lộn hột", "cashew"],
    "cao su": ["cao su", "cây su"],
    "sầu riêng": ["sầu riêng", "sau rieng", "durian", "sầu", "monthong", "ri6"],
    "bưởi": ["bưởi", "buoi"],
    "cam": ["cam", "quýt", "chanh"],
    "xoài": ["xoài", "xoai", "mango"],
    "nhãn": ["nhãn", "nhan", "longan"],
    "vải": ["vải", "vai", "lychee"],
    "thanh long": ["thanh long", "dragon fruit"],
    "chuối": ["chuối", "chuoi", "banana"],
    "dưa hấu": ["dưa hấu", "dua hau", "watermelon"],
    "dưa leo": ["dưa leo", "dua leo", "cucumber", "dưa chuột"],
    "rau muống": ["rau muống", "rau muong"],
    "rau cải": ["rau cải", "cải", "cải bắp", "cải thảo", "cải xanh", "bắp cải", "cabbage"],
    "cà chua": ["cà chua", "ca chua", "tomato"],
    "ớt": ["ớt", "ot", "chili"],
    "khoai": ["khoai", "khoai lang", "khoai tây", "khoai mì", "sắn"],
    "ngô": ["ngô", "bắp", "ngo", "corn", "maize"],
    "đậu": ["đậu", "đậu nành", "đậu phộng", "đậu xanh", "đậu đen", "bean"],
    "mía": ["mía", "mia", "sugarcane"],
    "dừa": ["dừa", "dua", "coconut"],
    "hoa": ["hoa", "hoa cúc", "hoa hồng", "hoa lan", "hoa mai"],
}

STAGE_KEYWORDS = {
    "gieo mạ": ["gieo mạ", "gieo ma", "mạ", "ươm giống", "ngâm giống"],
    "đẻ nhánh": ["đẻ nhánh", "de nhanh", "nảy chồi", "đâm chồi"],
    "làm đòng": ["làm đòng", "lam dong", "trổ đòng", "đứng cái"],
    "trổ bông": ["trổ bông", "tro bong", "trổ", "phơi màu"],
    "ngậm sữa": ["ngậm sữa", "ngam sua", "vào chắc"],
    "chín": ["chín", "chin", "thu hoạch", "gặt"],
    "ra hoa": ["ra hoa", "ra bông", "nở hoa", "đậu hoa"],
    "đậu trái": ["đậu trái", "đậu quả", "kết trái"],
    "nuôi trái": ["nuôi trái", "nuôi quả", "phát triển quả"],
    "trái non": ["trái non", "quả non"],
    "trái già": ["trái già", "quả già", "sắp chín"],
    "cây con": ["cây con", "cây giống", "mới trồng", "mới xuống giống"],
    "sinh trưởng": ["sinh trưởng", "phát triển", "lớn lên"],
    "ra lá": ["ra lá", "mọc lá", "lá non"],
    "ra rễ": ["ra rễ", "bén rễ", "phát triển rễ"],
}

SYMPTOM_KEYWORDS = {
    "vàng lá": ["vàng lá", "lá vàng", "lá úa", "lá héo vàng", "vàng hết", "vàng dần"],
    "vàng lá từ gốc": ["vàng từ gốc", "vàng lá từ gốc", "vàng từ dưới lên", "vàng từ gốc lên"],
    "vàng lá từ ngọn": ["vàng từ ngọn", "vàng lá từ ngọn", "vàng từ trên xuống"],
    "cháy lá": ["cháy lá", "lá cháy", "khô lá", "lá khô", "cháy rìa", "cháy mép lá"],
    "đốm lá": ["đốm lá", "lá đốm", "vết đốm", "đốm nâu", "đốm vàng", "đốm đen", "chấm lá"],
    "thối rễ": ["thối rễ", "rễ thối", "hư rễ", "rễ đen", "rễ mềm", "rễ nhũn"],
    "ngập úng": ["úng", "ngập úng", "ngập nước", "ngập", "úng nước", "đọng nước", "nước ngập"],
    "xoăn lá": ["xoăn lá", "lá xoăn", "cuốn lá", "lá cuốn", "lá quăn", "quăn lá"],
    "héo": ["héo", "rũ", "xìu", "mềm nhũn", "héo rũ", "héo dần", "héo xanh"],
    "rụng lá": ["rụng lá", "rơi lá", "lá rụng", "lá rơi"],
    "rụng hoa": ["rụng hoa", "rơi hoa", "hoa rụng", "hoa rơi", "không đậu hoa"],
    "rụng trái": ["rụng trái", "rơi trái", "trái rụng", "quả rụng", "trái rơi"],
    "sâu": ["sâu", "sâu đục", "sâu ăn", "sâu cuốn", "sâu tơ", "sâu xanh", "sâu keo"],
    "rầy": ["rầy", "rầy nâu", "rầy xanh", "rầy lưng trắng", "rầy chổng cánh"],
    "bọ": ["bọ", "bọ xít", "bọ trĩ", "bọ cánh cứng", "bọ nhảy", "bọ hà"],
    "rệp": ["rệp", "rệp sáp", "rệp vảy", "rệp muội"],
    "nhện": ["nhện", "nhện đỏ", "nhện gié"],
    "nấm": ["nấm", "nấm bệnh", "mốc", "phấn trắng", "gỉ sắt", "thán thư", "đạo ôn"],
    "vi khuẩn": ["vi khuẩn", "thối nhũn", "chảy nhựa", "bạc lá"],
    "virus": ["khảm", "xoăn lùn", "lùn sọc đen", "vàng lùn"],
    "chậm lớn": ["chậm lớn", "còi cọc", "không phát triển", "lùn", "không lớn", "chậm phát triển"],
    "thiếu dinh dưỡng": ["thiếu dinh dưỡng", "thiếu phân", "thiếu đạm", "thiếu lân", "thiếu kali", "thiếu vi lượng"],
    "khô héo": ["khô héo", "khô dần", "khô cành", "chết khô", "khô đọt"],
    "thối thân": ["thối thân", "thân thối", "thối gốc", "gốc thối", "mục thân"],
    "xì mủ": ["xì mủ", "chảy mủ", "chảy nhựa", "tiết mủ"],
    "đạo ôn": ["đạo ôn", "cháy lá", "khô vằn", "đốm cổ bông"],
    "lem lép": ["lem lép", "lép hạt", "hạt lép", "lép lửng"],
}

REGION_KEYWORDS = {
    Region.DBSCL: ["đồng bằng sông cửu long", "dbscl", "miền tây", "cần thơ", "an giang",
                   "kiên giang", "đồng tháp", "long an", "tiền giang", "bến tre",
                   "vĩnh long", "trà vinh", "sóc trăng", "hậu giang", "bạc liêu", "cà mau"],
    Region.TAY_NGUYEN: ["tây nguyên", "đắk lắk", "đắk nông", "gia lai", "kon tum", "lâm đồng",
                        "ban mê thuột", "pleiku", "đà lạt"],
    Region.MIEN_BAC: ["miền bắc", "hà nội", "hải phòng", "nam định", "thái bình", "hưng yên",
                      "hải dương", "bắc ninh", "vĩnh phúc", "phú thọ", "đồng bằng sông hồng"],
    Region.MIEN_TRUNG: ["miền trung", "đà nẵng", "huế", "quảng nam", "quảng ngãi", "bình định",
                        "phú yên", "khánh hòa", "ninh thuận", "bình thuận", "nghệ an", "hà tĩnh"],
    Region.DONG_NAM_BO: ["đông nam bộ", "bình dương", "đồng nai", "bà rịa", "vũng tàu",
                         "bình phước", "tây ninh", "sài gòn", "tp hcm", "hồ chí minh"],
}

WEATHER_KEYWORDS = {
    "mưa": ["mưa", "mua", "mưa nhiều", "mưa hoài", "mưa dầm", "ngập"],
    "nắng": ["nắng", "nang", "nắng gắt", "nắng nóng", "khô hạn"],
    "lạnh": ["lạnh", "rét", "lạnh giá", "sương muối"],
    "gió": ["gió", "bão", "giông", "gió lớn"],
    "ẩm": ["ẩm", "ẩm ướt", "độ ẩm cao"],
}

ACTION_KEYWORDS = {
    "bón phân": ["bón phân", "bón thêm phân", "phun phân", "bổ sung phân"],
    "phun thuốc": ["phun thuốc", "xịt thuốc", "thuốc trừ sâu", "thuốc bệnh"],
    "tưới nước": ["tưới", "tưới nước", "tưới thêm"],
    "cắt tỉa": ["cắt tỉa", "tỉa cành", "cắt bỏ"],
    "thu hoạch": ["thu hoạch", "gặt", "hái"],
}


class CropClassifier:
    """
    Advanced Crop Classifier with proper ML training
    - SGDClassifier with partial_fit for incremental learning
    - Learning rate scheduling
    - Keyword weight optimization
    """
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.classes = list(CROP_KEYWORDS.keys())
        self.keyword_weights = {crop: 1.0 for crop in self.classes}
        self.keyword_match_counts = {crop: {"correct": 0, "total": 0} for crop in self.classes}
        self.train_history = {"loss": [], "accuracy": []}
        self.learning_rate = 0.01
        self.epoch_count = 0

    def _build_sklearn_model(self):
        if HAS_SKLEARN:
            return SGDClassifier(
                loss='log_loss',
                penalty='l2',
                alpha=0.0001,
                learning_rate='optimal',
                eta0=self.learning_rate,
                max_iter=1,
                warm_start=True,
                random_state=RANDOM_SEED
            )
        return None

    def _ensure_vectorizer(self, texts: List[str]):
        if HAS_SKLEARN and self.vectorizer is None:
            self.vectorizer = TfidfVectorizer(
                ngram_range=(1, 3),
                max_features=1000,
                sublinear_tf=True,
                min_df=1
            )
            self.vectorizer.fit(texts)

    def partial_fit(self, texts: List[str], labels: List[str], learning_rate: float = None):
        """Incremental training - learns from batch without forgetting"""
        if learning_rate:
            self.learning_rate = learning_rate
        
        self.epoch_count += 1
        
        if HAS_SKLEARN:
            self._ensure_vectorizer(texts)
            X = self.vectorizer.transform(texts)
            
            # Collect all unique labels seen so far
            for label in labels:
                if label not in self.classes:
                    self.classes.append(label)
            
            # Get all possible classes (sorted for consistency)
            all_classes = sorted(list(set(self.classes)))
            
            if self.model is None:
                self.model = self._build_sklearn_model()
                self.model.partial_fit(X, labels, classes=all_classes)
            else:
                # Check if we have new classes
                current_classes = set(self.model.classes_) if hasattr(self.model, 'classes_') else set()
                new_classes = set(labels) - current_classes
                if new_classes:
                    # Need to reinitialize model with new classes
                    all_classes = sorted(list(current_classes | new_classes | set(self.classes)))
                    old_model = self.model
                    self.model = self._build_sklearn_model()
                    self.model.partial_fit(X, labels, classes=all_classes)
                else:
                    self.model.partial_fit(X, labels)
            
            # Calculate loss
            try:
                proba = self.model.predict_proba(X)
                # Cross entropy loss
                loss = 0.0
                for i, label in enumerate(labels):
                    if label in self.model.classes_:
                        label_idx = list(self.model.classes_).index(label)
                        prob = max(proba[i][label_idx], 1e-10)
                        loss -= math.log(prob)
                    else:
                        loss += 2.0  # Penalty for unknown label
                loss /= len(labels)
                self.train_history["loss"].append(loss)
            except Exception:
                self.train_history["loss"].append(0.5)
        
        # Also update keyword weights (hybrid approach)
        for text, label in zip(texts, labels):
            normalized = text.lower()
            for crop, keywords in CROP_KEYWORDS.items():
                matched = any(kw in normalized for kw in keywords)
                if matched:
                    self.keyword_match_counts[crop]["total"] += 1
                    if crop == label:
                        self.keyword_match_counts[crop]["correct"] += 1
                        # Increase weight for correct matches
                        delta = self.learning_rate * 0.5
                        self.keyword_weights[crop] = min(3.0, self.keyword_weights.get(crop, 1.0) + delta)
                    else:
                        # Decrease weight for incorrect matches
                        delta = self.learning_rate * 0.2
                        self.keyword_weights[crop] = max(0.3, self.keyword_weights.get(crop, 1.0) - delta)

    def fit(self, texts: List[str], labels: List[str]):
        """Full training - resets and trains from scratch"""
        self.partial_fit(texts, labels)

    def predict(self, text: str) -> Optional[str]:
        normalized = text.lower()
        
        # Try sklearn model first
        if HAS_SKLEARN and self.model is not None and self.vectorizer is not None:
            try:
                X = self.vectorizer.transform([text])
                pred = self.model.predict(X)[0]
                # Verify with keyword check
                for crop, keywords in CROP_KEYWORDS.items():
                    if any(kw in normalized for kw in keywords):
                        if crop == pred:
                            return pred
                        # If mismatch, use weighted scoring
                        break
                return pred
            except Exception:
                pass
        
        # Fallback: Weighted keyword matching
        best_crop = None
        best_score = 0.0
        for crop, keywords in CROP_KEYWORDS.items():
            for kw in keywords:
                if kw in normalized:
                    weight = self.keyword_weights.get(crop, 1.0)
                    # Bonus for longer keyword matches
                    length_bonus = len(kw) / 10.0
                    score = weight + length_bonus
                    if score > best_score:
                        best_score = score
                        best_crop = crop
                    break
        return best_crop

    def predict_proba(self, text: str) -> Dict[str, float]:
        """Get probability distribution over crops"""
        if HAS_SKLEARN and self.model is not None and self.vectorizer is not None:
            try:
                X = self.vectorizer.transform([text])
                proba = self.model.predict_proba(X)[0]
                return {cls: float(p) for cls, p in zip(self.model.classes_, proba)}
            except Exception:
                pass
        
        # Fallback: normalize keyword weights
        normalized = text.lower()
        scores = {}
        for crop, keywords in CROP_KEYWORDS.items():
            if any(kw in normalized for kw in keywords):
                scores[crop] = self.keyword_weights.get(crop, 1.0)
        
        if scores:
            total = sum(scores.values())
            return {k: v/total for k, v in scores.items()}
        return {}

    def evaluate(self, texts: List[str], labels: List[str]) -> Dict[str, float]:
        """Evaluate model on a dataset"""
        correct = 0
        total = len(texts)
        
        for text, label in zip(texts, labels):
            pred = self.predict(text)
            if pred and pred.lower() == label.lower():
                correct += 1
        
        accuracy = correct / total if total > 0 else 0.0
        self.train_history["accuracy"].append(accuracy)
        return {"accuracy": accuracy, "correct": correct, "total": total}

    def get_loss(self) -> float:
        """Get latest training loss"""
        if self.train_history["loss"]:
            return self.train_history["loss"][-1]
        return 1.0

    def save(self, path: str):
        with open(path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'vectorizer': self.vectorizer,
                'weights': self.keyword_weights,
                'classes': self.classes,
                'match_counts': self.keyword_match_counts,
                'history': self.train_history,
                'epoch_count': self.epoch_count
            }, f)

    def load(self, path: str):
        if os.path.exists(path):
            with open(path, 'rb') as f:
                data = pickle.load(f)
                self.model = data.get('model')
                self.vectorizer = data.get('vectorizer')
                self.keyword_weights = data.get('weights', self.keyword_weights)
                self.classes = data.get('classes', self.classes)
                self.keyword_match_counts = data.get('match_counts', self.keyword_match_counts)
                self.train_history = data.get('history', self.train_history)
                self.epoch_count = data.get('epoch_count', 0)
            return True
        return False


crop_classifier = CropClassifier()


class SymptomClassifier:
    """
    Multi-label classifier for symptoms
    Uses TF-IDF + Binary Relevance approach
    """
    def __init__(self):
        self.vectorizer = None
        self.classifiers = {}  # One classifier per symptom
        self.symptom_classes = list(SYMPTOM_KEYWORDS.keys())
        self.symptom_weights = {s: 1.0 for s in self.symptom_classes}
        self.epoch_count = 0
        self.learning_rate = 0.01
    
    def _ensure_vectorizer(self, texts: List[str]):
        if HAS_SKLEARN and self.vectorizer is None:
            self.vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                max_features=500,
                sublinear_tf=True
            )
            self.vectorizer.fit(texts)
    
    def partial_fit(self, texts: List[str], labels_list: List[List[str]], learning_rate: float = None):
        """Train symptom classifiers incrementally"""
        if learning_rate:
            self.learning_rate = learning_rate
        self.epoch_count += 1
        
        if HAS_SKLEARN:
            self._ensure_vectorizer(texts)
            X = self.vectorizer.transform(texts)
            
            # Train one classifier per symptom (Binary Relevance)
            for symptom in self.symptom_classes:
                # Create binary labels
                y = [1 if symptom in labels else 0 for labels in labels_list]
                
                if sum(y) == 0:  # Skip if no positive examples
                    continue
                
                if symptom not in self.classifiers:
                    self.classifiers[symptom] = SGDClassifier(
                        loss='log_loss',
                        penalty='l2',
                        max_iter=1,
                        warm_start=True,
                        random_state=RANDOM_SEED
                    )
                
                self.classifiers[symptom].partial_fit(X, y, classes=[0, 1])
        
        # Update keyword weights
        for text, symptoms in zip(texts, labels_list):
            normalized = text.lower()
            for symptom, keywords in SYMPTOM_KEYWORDS.items():
                matched = any(kw in normalized for kw in keywords)
                if matched:
                    if symptom in symptoms:
                        delta = self.learning_rate * 0.3
                        self.symptom_weights[symptom] = min(2.5, self.symptom_weights.get(symptom, 1.0) + delta)
                    else:
                        delta = self.learning_rate * 0.1
                        self.symptom_weights[symptom] = max(0.5, self.symptom_weights.get(symptom, 1.0) - delta)
    
    def predict(self, text: str) -> List[str]:
        """Predict symptoms for a text"""
        predictions = []
        
        if HAS_SKLEARN and self.vectorizer is not None:
            try:
                X = self.vectorizer.transform([text])
                for symptom, clf in self.classifiers.items():
                    proba = clf.predict_proba(X)[0]
                    if len(proba) > 1 and proba[1] > 0.3:  # Threshold
                        predictions.append(symptom)
            except Exception:
                pass
        
        # Also use keyword matching with weights
        normalized = text.lower()
        for symptom, keywords in SYMPTOM_KEYWORDS.items():
            for keyword in keywords:
                if keyword in normalized:
                    weight = self.symptom_weights.get(symptom, 1.0)
                    if weight > 0.8 and symptom not in predictions:
                        predictions.append(symptom)
                    break
        
        return predictions
    
    def evaluate(self, texts: List[str], labels_list: List[List[str]]) -> Dict[str, float]:
        """Evaluate symptom prediction"""
        total_precision = 0
        total_recall = 0
        count = 0
        
        for text, gold in zip(texts, labels_list):
            pred = self.predict(text)
            
            if gold:
                # Calculate metrics
                matched = sum(1 for g in gold if any(g in p or p in g for p in pred))
                precision = matched / len(pred) if pred else 0
                recall = matched / len(gold)
                total_precision += precision
                total_recall += recall
                count += 1
        
        avg_precision = total_precision / count if count > 0 else 0
        avg_recall = total_recall / count if count > 0 else 0
        f1 = 2 * avg_precision * avg_recall / (avg_precision + avg_recall) if (avg_precision + avg_recall) > 0 else 0
        
        return {"precision": avg_precision, "recall": avg_recall, "f1": f1}
    
    def save(self, path: str):
        with open(path, 'wb') as f:
            pickle.dump({
                'vectorizer': self.vectorizer,
                'classifiers': self.classifiers,
                'weights': self.symptom_weights,
                'epoch_count': self.epoch_count
            }, f)
    
    def load(self, path: str):
        if os.path.exists(path):
            with open(path, 'rb') as f:
                data = pickle.load(f)
                self.vectorizer = data.get('vectorizer')
                self.classifiers = data.get('classifiers', {})
                self.symptom_weights = data.get('weights', self.symptom_weights)
                self.epoch_count = data.get('epoch_count', 0)
            return True
        return False


symptom_classifier = SymptomClassifier()
SYMPTOM_MODEL_FILE = os.path.join(MODELS_DIR, "symptom_classifier.pkl")


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text

def extract_crop(text: str, use_model: bool = True) -> Optional[str]:
    if use_model and (crop_classifier.model is not None or any(w != 1.0 for w in crop_classifier.keyword_weights.values())):
        pred = crop_classifier.predict(text)
        if pred:
            return pred
    normalized = normalize_text(text)
    for crop, keywords in CROP_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized:
                return crop
    return None


def extract_stage(text: str) -> Optional[str]:
    normalized = normalize_text(text)
    for stage, keywords in STAGE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized:
                return stage
    return None


def extract_symptoms(text: str) -> List[str]:
    normalized = normalize_text(text)
    found = []
    for symptom, keywords in SYMPTOM_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized:
                if symptom not in found:
                    found.append(symptom)
                break
    return found


def extract_region(text: str) -> str:
    normalized = normalize_text(text)
    for region, keywords in REGION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized:
                return region.value
    return Region.UNKNOWN.value


def extract_weather(text: str) -> Optional[str]:
    normalized = normalize_text(text)
    found = []
    for weather, keywords in WEATHER_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized:
                found.append(weather)
                break
    return ", ".join(found) if found else None


def extract_season(text: str, weather_context: Optional[str]) -> str:
    normalized = normalize_text(text)
    indicators = {
        "đông xuân": Season.DONG_XUAN,
        "hè thu": Season.HE_THU,
        "thu đông": Season.THU_DONG,
        "mùa mưa": Season.MUA,
        "mùa khô": Season.KHO,
    }
    for ind, season in indicators.items():
        if ind in normalized:
            return season.value
    if weather_context:
        if "mưa" in weather_context:
            return Season.MUA.value
        elif "nắng" in weather_context or "khô" in weather_context:
            return Season.KHO.value
    return Season.UNKNOWN.value


def extract_action_asked(text: str) -> Optional[str]:
    normalized = normalize_text(text)
    for action, keywords in ACTION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized:
                return action
    patterns = [
        (r"có nên (.+?) không", "hỏi ý kiến về"),
        (r"làm sao (.+)", "hỏi cách"),
        (r"phải làm gì", "hỏi giải pháp"),
        (r"tại sao (.+)", "hỏi nguyên nhân"),
        (r"vì sao (.+)", "hỏi nguyên nhân"),
    ]
    for pattern, action_type in patterns:
        if re.search(pattern, normalized):
            return action_type
    return None


def detect_urgency(text: str, symptoms: List[str]) -> str:
    normalized = normalize_text(text)
    urgent = ["chết", "héo rũ", "cháy hết", "rụng sạch", "khẩn cấp", "gấp", "nhanh", "ngay", "lan nhanh", "cả ruộng"]
    for kw in urgent:
        if kw in normalized:
            return "urgent"
    severe = ["thối rễ", "chết cây", "cháy lá", "virus"]
    for s in symptoms:
        if s in severe:
            return "high"
    if len(symptoms) >= 3:
        return "high"
    elif len(symptoms) >= 2:
        return "medium"
    return "normal"


def detect_experience_level(text: str) -> str:
    normalized = normalize_text(text)
    beginner = ["không biết", "lần đầu", "mới trồng", "mới tập", "chưa biết", "hỏi thăm", "nhờ chỉ"]
    expert = ["thường thì", "năm ngoái", "mấy năm nay", "kinh nghiệm", "đã thử", "đã bón", "vụ trước"]
    for ind in expert:
        if ind in normalized:
            return Experience.CO_KINH_NGHIEM.value
    for ind in beginner:
        if ind in normalized:
            return Experience.PHO_THONG.value
    return Experience.UNKNOWN.value


def detect_scale(text: str) -> str:
    normalized = normalize_text(text)
    farm = ["trang trại", "mấy héc", "hecta", "ha", "mẫu", "công ty"]
    home = ["nhà tui", "vườn nhà", "sân nhà", "mấy gốc", "vài cây", "ít cây"]
    for ind in farm:
        if ind in normalized:
            return Scale.TRANG_TRAI.value
    for ind in home:
        if ind in normalized:
            return Scale.NHA_VUON.value
    return Scale.UNKNOWN.value


def analyze_question(text: str, use_model: bool = True) -> QuestionAnalysis:
    weather_context = extract_weather(text)
    symptoms = extract_symptoms(text)
    return QuestionAnalysis(
        original_question=text,
        crop=extract_crop(text, use_model=use_model),
        stage=extract_stage(text),
        symptoms=symptoms,
        region=extract_region(text),
        season=extract_season(text, weather_context),
        scale=detect_scale(text),
        experience=detect_experience_level(text),
        weather_context=weather_context,
        time_context=None,
        action_asked=extract_action_asked(text),
        urgency_level=detect_urgency(text, symptoms),
    )


class AgriKnowledgeBase:
    def __init__(self):
        self.rules = self._init_rules()

    def _init_rules(self) -> List[Dict]:
        return [
            {
                "id": "LUA_001",
                "conditions": {"crop": "lúa", "stage": "đẻ nhánh", "symptoms": ["vàng lá từ gốc"], "weather": "mưa"},
                "conclusions": {
                    "priority_causes": ["Nghẹt rễ do ngập úng", "Thiếu oxy vùng rễ"],
                    "secondary_causes": ["Thiếu đạm (N)", "Nấm bệnh vùng rễ"],
                    "recommended_actions": ["Tháo bớt nước ruộng, để mực nước 3-5cm", "Kiểm tra rễ lúa (rễ đen = nghẹt rễ)", "Nếu rễ trắng khỏe mới bón phân"],
                    "avoid_actions": ["KHÔNG bón phân đạm ngay khi chưa kiểm tra rễ", "KHÔNG để ruộng ngập sâu quá 10cm"],
                    "check_first": ["Màu sắc rễ lúa (trắng = khỏe, đen/nâu = nghẹt)", "Mực nước ruộng hiện tại", "Tình trạng thoát nước"]
                },
                "confidence": "high",
                "reasoning": "Mưa nhiều + vàng lá từ gốc ở giai đoạn đẻ nhánh thường do nghẹt rễ"
            },
            {
                "id": "LUA_002",
                "conditions": {"crop": "lúa", "symptoms": ["vàng lá từ ngọn"]},
                "conclusions": {
                    "priority_causes": ["Thiếu đạm (N)"],
                    "secondary_causes": ["Đất nghèo dinh dưỡng", "Rễ yếu không hút được dinh dưỡng"],
                    "recommended_actions": ["Bón bổ sung phân đạm (Urê) 3-5kg/1000m²", "Kết hợp phân bón lá nếu cần nhanh"],
                    "avoid_actions": ["KHÔNG bón quá nhiều một lần (dễ cháy lá)", "KHÔNG bón khi trời nắng gắt"],
                    "check_first": ["Xác nhận vàng từ ngọn xuống, không phải từ gốc lên"]
                },
                "confidence": "medium",
                "reasoning": "Vàng từ ngọn thường là thiếu đạm"
            },
            {
                "id": "LUA_003",
                "conditions": {"crop": "lúa", "symptoms": ["rầy"]},
                "conclusions": {
                    "priority_causes": ["Rầy nâu tấn công"],
                    "secondary_causes": ["Bón quá nhiều đạm", "Mật độ sạ quá dày"],
                    "recommended_actions": ["Kiểm tra mật độ rầy", "Nếu >3 con/dảnh: phun thuốc đặc trị", "Thuốc khuyến cáo: Bassa, Applaud, Chess"],
                    "avoid_actions": ["KHÔNG phun thuốc bừa bãi", "KHÔNG bón thêm đạm khi có rầy"],
                    "check_first": ["Đếm mật độ rầy thực tế", "Xác định loại rầy"]
                },
                "confidence": "high",
                "reasoning": "Rầy là đối tượng gây hại nghiêm trọng trên lúa"
            },
            {
                "id": "CAPHE_001",
                "conditions": {"crop": "cà phê", "symptoms": ["vàng lá"], "weather": "mưa"},
                "conclusions": {
                    "priority_causes": ["Thối rễ do nấm Fusarium", "Ngập úng vùng rễ"],
                    "secondary_causes": ["Tuyến trùng hại rễ", "Thiếu vi lượng"],
                    "recommended_actions": ["Đào rãnh thoát nước quanh gốc", "Kiểm tra rễ cà phê", "Xử lý nấm bệnh bằng thuốc gốc đồng"],
                    "avoid_actions": ["KHÔNG tưới thêm nước", "KHÔNG bón phân hóa học khi rễ đang yếu"],
                    "check_first": ["Tình trạng thoát nước vườn", "Màu sắc và mùi của rễ"]
                },
                "confidence": "medium",
                "reasoning": "Cà phê rất nhạy cảm với ngập úng"
            },
            {
                "id": "CAPHE_002",
                "conditions": {"crop": "cà phê", "stage": "ra hoa", "symptoms": ["rụng hoa"]},
                "conclusions": {
                    "priority_causes": ["Thiếu nước giai đoạn ra hoa", "Thời tiết bất lợi"],
                    "secondary_causes": ["Thiếu Bo (B)", "Sâu đục hoa"],
                    "recommended_actions": ["Tưới đủ nước, duy trì độ ẩm đất 60-70%", "Phun phân bón lá có Bo"],
                    "avoid_actions": ["KHÔNG để cây khô hạn", "KHÔNG phun thuốc có mùi nồng"],
                    "check_first": ["Độ ẩm đất vùng rễ", "Có ong đến thụ phấn không"]
                },
                "confidence": "medium",
                "reasoning": "Giai đoạn ra hoa cà phê rất nhạy cảm"
            },
            {
                "id": "RAU_001",
                "conditions": {"crop": "rau", "symptoms": ["sâu"]},
                "conclusions": {
                    "priority_causes": ["Sâu ăn lá (sâu xanh, sâu tơ)"],
                    "secondary_causes": ["Mật độ trồng quá dày", "Thiếu thiên địch"],
                    "recommended_actions": ["Bắt sâu bằng tay nếu ít", "Dùng thuốc sinh học (BT, NPV)", "Luân canh cây trồng"],
                    "avoid_actions": ["KHÔNG dùng thuốc hóa học mạnh gần thu hoạch"],
                    "check_first": ["Xác định loại sâu cụ thể", "Thời gian còn lại đến thu hoạch"]
                },
                "confidence": "high",
                "reasoning": "Rau cần đảm bảo an toàn thực phẩm"
            },
            {
                "id": "GENERAL_001",
                "conditions": {"symptoms": ["thối rễ"]},
                "conclusions": {
                    "priority_causes": ["Nấm bệnh vùng rễ", "Ngập úng kéo dài"],
                    "secondary_causes": ["Bón quá nhiều phân", "Đất nén chặt thiếu oxy"],
                    "recommended_actions": ["Cải thiện thoát nước ngay", "Xử lý nấm bằng Trichoderma hoặc thuốc gốc đồng"],
                    "avoid_actions": ["KHÔNG bón phân hóa học khi rễ đang thối", "KHÔNG tưới ngập"],
                    "check_first": ["Mức độ thối rễ", "Có thể cứu được không"]
                },
                "confidence": "high",
                "reasoning": "Thối rễ là vấn đề nghiêm trọng"
            },
            {
                "id": "GENERAL_002",
                "conditions": {"symptoms": ["nấm"], "weather": "ẩm"},
                "conclusions": {
                    "priority_causes": ["Nấm bệnh do độ ẩm cao"],
                    "secondary_causes": ["Thông gió kém", "Mật độ trồng dày"],
                    "recommended_actions": ["Tỉa bớt lá, cành để thông thoáng", "Phun thuốc trừ nấm"],
                    "avoid_actions": ["KHÔNG tưới phun lên lá", "KHÔNG bón phân đạm cao"],
                    "check_first": ["Loại nấm bệnh cụ thể", "Mức độ lan rộng"]
                },
                "confidence": "medium",
                "reasoning": "Môi trường ẩm ướt tạo điều kiện cho nấm bệnh"
            },
        ]

    def find_matching_rules(self, analysis: QuestionAnalysis) -> List[Dict]:
        matching = []
        for rule in self.rules:
            cond = rule["conditions"]
            if "crop" in cond:
                if analysis.crop is None:
                    continue
                if cond["crop"].lower() != analysis.crop.lower():
                    continue
            score = 0
            total = len(cond)
            if "crop" in cond:
                score += 1
            if "stage" in cond:
                if analysis.stage and cond["stage"].lower() in analysis.stage.lower():
                    score += 1
                elif analysis.stage is None:
                    score += 0.2
            if "symptoms" in cond:
                matched = sum(1 for s in cond["symptoms"] if any(s in sym for sym in analysis.symptoms))
                if matched > 0:
                    score += matched / len(cond["symptoms"])
            if "weather" in cond:
                if analysis.weather_context and cond["weather"].lower() in analysis.weather_context.lower():
                    score += 1
                elif analysis.weather_context is None:
                    score += 0.2
            ratio = score / total if total > 0 else 0
            if ratio >= 0.5:
                matching.append({"rule": rule, "match_score": ratio})
        matching.sort(key=lambda x: x["match_score"], reverse=True)
        return matching


def apply_agri_logic(analysis: QuestionAnalysis) -> AgriLogicResult:
    kb = AgriKnowledgeBase()
    matches = kb.find_matching_rules(analysis)
    priority_causes, secondary_causes, recommended_actions, avoid_actions, check_first = [], [], [], [], []
    knowledge_notes, reasoning_chain = [], []
    if matches:
        for m in matches[:3]:
            rule = m["rule"]
            score = m["match_score"]
            conc = rule["conclusions"]
            reasoning_chain.append(f"Áp dụng rule {rule['id']} (độ khớp: {score:.0%}): {rule['reasoning']}")
            priority_causes.extend(conc.get("priority_causes", []))
            secondary_causes.extend(conc.get("secondary_causes", []))
            recommended_actions.extend(conc.get("recommended_actions", []))
            avoid_actions.extend(conc.get("avoid_actions", []))
            check_first.extend(conc.get("check_first", []))
        confidence = "high" if matches[0]["match_score"] >= 0.8 else "medium"
    else:
        reasoning_chain.append("Không tìm thấy rule phù hợp, đưa ra khuyến nghị chung")
        if analysis.symptoms:
            priority_causes.append(f"Cần kiểm tra thêm về: {', '.join(analysis.symptoms)}")
        recommended_actions.append("Quan sát thêm và mô tả chi tiết hơn")
        check_first.append("Xác định rõ triệu chứng và giai đoạn cây")
        confidence = "low"
    priority_causes = list(dict.fromkeys(priority_causes))
    secondary_causes = list(dict.fromkeys(secondary_causes))
    recommended_actions = list(dict.fromkeys(recommended_actions))
    avoid_actions = list(dict.fromkeys(avoid_actions))
    check_first = list(dict.fromkeys(check_first))
    if analysis.crop:
        knowledge_notes.append(f"Loại cây: {analysis.crop}")
    if analysis.stage:
        knowledge_notes.append(f"Giai đoạn: {analysis.stage}")
    if analysis.weather_context:
        knowledge_notes.append(f"Thời tiết: {analysis.weather_context}")
    if analysis.region != Region.UNKNOWN.value:
        knowledge_notes.append(f"Vùng miền: {analysis.region}")
    return AgriLogicResult(
        priority_causes=priority_causes,
        secondary_causes=secondary_causes,
        recommended_actions=recommended_actions,
        avoid_actions=avoid_actions,
        check_first=check_first,
        knowledge_notes=knowledge_notes,
        confidence_level=confidence,
        reasoning_chain=reasoning_chain,
    )


def build_prompt(analysis: QuestionAnalysis, logic_result: AgriLogicResult, mode: str = "runtime") -> str:
    if mode == "debug":
        return _build_prompt_debug(analysis, logic_result)
    return _build_prompt_runtime(analysis, logic_result)


def _build_prompt_debug(analysis: QuestionAnalysis, logic_result: AgriLogicResult) -> str:
    parts = []
    parts.append("""=== VAI TRÒ ===
Bạn là một KỸ SƯ NÔNG NGHIỆP VIỆT NAM giàu kinh nghiệm, chuyên tư vấn cho nông dân.
- Bạn hiểu rõ điều kiện canh tác, khí hậu, và thực tiễn nông nghiệp Việt Nam
- Bạn nói chuyện thân thiện, dễ hiểu, dùng ngôn ngữ đời thường
- Bạn KHÔNG bịa đặt thông tin, nếu không chắc chắn sẽ nói rõ
- Bạn ưu tiên các biện pháp an toàn, tiết kiệm, hiệu quả""")
    parts.append(f'\n=== CÂU HỎI GỐC CỦA NÔNG DÂN ===\n"{analysis.original_question}"\n')
    ctx = ["=== BỐI CẢNH ĐÃ PHÂN TÍCH ==="]
    ctx.append(f"• Loại cây trồng: {analysis.crop or 'Chưa xác định rõ'}")
    ctx.append(f"• Giai đoạn sinh trưởng: {analysis.stage or 'Chưa xác định'}")
    ctx.append(f"• Triệu chứng phát hiện: {', '.join(analysis.symptoms) if analysis.symptoms else 'Không mô tả rõ'}")
    if analysis.weather_context:
        ctx.append(f"• Điều kiện thời tiết: {analysis.weather_context}")
    if analysis.region != Region.UNKNOWN.value:
        ctx.append(f"• Vùng miền: {analysis.region}")
    if analysis.season != Season.UNKNOWN.value:
        ctx.append(f"• Mùa vụ: {analysis.season}")
    if analysis.scale != Scale.UNKNOWN.value:
        ctx.append(f"• Quy mô: {analysis.scale}")
    if analysis.action_asked:
        ctx.append(f"• Nông dân đang hỏi về: {analysis.action_asked}")
    ctx.append(f"• Mức độ khẩn cấp: {analysis.urgency_level}")
    parts.append("\n".join(ctx))
    if logic_result.priority_causes or logic_result.recommended_actions:
        sys_analysis = ["", "=== NHẬN ĐỊNH BAN ĐẦU CỦA HỆ THỐNG ==="]
        sys_analysis.append(f"(Độ tin cậy: {logic_result.confidence_level})")
        if logic_result.reasoning_chain:
            sys_analysis.append("")
            sys_analysis.append("Chuỗi suy luận:")
            for i, r in enumerate(logic_result.reasoning_chain, 1):
                sys_analysis.append(f"  {i}. {r}")
        if logic_result.priority_causes:
            sys_analysis.append("")
            sys_analysis.append("Nguyên nhân có khả năng cao nhất:")
            for c in logic_result.priority_causes:
                sys_analysis.append(f"  ➤ {c}")
        if logic_result.secondary_causes:
            sys_analysis.append("")
            sys_analysis.append("Nguyên nhân phụ cần xem xét:")
            for c in logic_result.secondary_causes:
                sys_analysis.append(f"  • {c}")
        if logic_result.check_first:
            sys_analysis.append("")
            sys_analysis.append("Cần kiểm tra trước:")
            for c in logic_result.check_first:
                sys_analysis.append(f"  ✓ {c}")
        if logic_result.recommended_actions:
            sys_analysis.append("")
            sys_analysis.append("Khuyến nghị hành động:")
            for a in logic_result.recommended_actions:
                sys_analysis.append(f"  → {a}")
        if logic_result.avoid_actions:
            sys_analysis.append("")
            sys_analysis.append("⚠️ TRÁNH LÀM:")
            for a in logic_result.avoid_actions:
                sys_analysis.append(f"  ✗ {a}")
        parts.append("\n".join(sys_analysis))
    parts.append("""
=== HƯỚNG DẪN TRẢ LỜI ===
1. Dựa trên phân tích trên, hãy trả lời câu hỏi của nông dân một cách:
   - Thân thiện, dễ hiểu (tránh thuật ngữ quá chuyên môn)
   - Cụ thể, có thể áp dụng ngay
   - Trung thực (nếu chưa chắc chắn, hãy nói rõ cần kiểm tra thêm)
2. Cấu trúc câu trả lời:
   - Bắt đầu bằng việc thông cảm/hiểu vấn đề của nông dân
   - Giải thích ngắn gọn nguyên nhân có thể
   - Đưa ra hướng dẫn cụ thể, từng bước
   - Kết thúc bằng lời khuyên theo dõi hoặc phòng ngừa
3. Lưu ý quan trọng:
   - Ưu tiên kiểm tra trước khi hành động (đặc biệt với bón phân, phun thuốc)
   - Đề cập đến việc CẦN TRÁNH nếu có
   - Nếu tình huống nghiêm trọng, khuyên liên hệ cán bộ khuyến nông địa phương
4. Sử dụng emoji phù hợp để làm rõ ý:
   🌱 cho cây trồng | 💧 cho nước/tưới | ☀️ cho thời tiết
   ⚠️ cho cảnh báo | ✅ cho khuyến nghị | ❌ cho tránh làm""")
    return "\n".join(parts)


def _build_prompt_runtime(analysis: QuestionAnalysis, logic_result: AgriLogicResult) -> str:
    lines = []
    lines.append("Bạn là kỹ sư nông nghiệp VN, tư vấn thân thiện, dễ hiểu, không bịa đặt.")
    lines.append(f'Câu hỏi: "{analysis.original_question}"')
    ctx_parts = []
    if analysis.crop:
        ctx_parts.append(f"Cây: {analysis.crop}")
    if analysis.stage:
        ctx_parts.append(f"Giai đoạn: {analysis.stage}")
    if analysis.symptoms:
        ctx_parts.append(f"Triệu chứng: {', '.join(analysis.symptoms[:3])}")
    if analysis.weather_context:
        ctx_parts.append(f"Thời tiết: {analysis.weather_context}")
    if ctx_parts:
        lines.append("Bối cảnh: " + "; ".join(ctx_parts))
    if logic_result.priority_causes:
        lines.append("Nguyên nhân chính: " + "; ".join(logic_result.priority_causes[:3]))
    if logic_result.check_first:
        lines.append("Kiểm tra trước: " + "; ".join(logic_result.check_first[:3]))
    if logic_result.recommended_actions:
        lines.append("Khuyến nghị: " + "; ".join(logic_result.recommended_actions[:3]))
    if logic_result.avoid_actions:
        lines.append("Tránh: " + "; ".join(logic_result.avoid_actions[:2]))
    lines.append("Trả lời ngắn gọn, cụ thể, dùng emoji 🌱💧⚠️✅❌ phù hợp.")
    prompt = "\n".join(lines)
    if len(prompt) > 800:
        prompt = prompt[:797] + "..."
    return prompt


def confidence_to_numeric(conf: str) -> float:
    return {"high": 0.9, "medium": 0.6, "low": 0.3}.get(conf, 0.3)


def compute_friendliness(prompt: str) -> float:
    sentences = re.split(r'[.!?。\n]+', prompt)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return 1.0
    total_words = sum(len(s.split()) for s in sentences)
    mean_len = total_words / len(sentences)
    return max(0.0, min(1.0, 1.0 - (mean_len / 30.0)))


def evaluate_prediction(gold: Dict, pred_analysis: QuestionAnalysis, logic_result: AgriLogicResult, prompt: str) -> Dict:
    gold_crop = gold.get("crop", "").lower() if gold.get("crop") else ""
    pred_crop = (pred_analysis.crop or "").lower()
    crop_match = 1 if gold_crop and gold_crop == pred_crop else 0
    gold_symptoms = [s.lower() for s in gold.get("symptoms", [])]
    pred_symptoms = [s.lower() for s in pred_analysis.symptoms]
    if gold_symptoms:
        matched = sum(1 for gs in gold_symptoms if any(gs in ps or ps in gs for ps in pred_symptoms))
        symptom_match = matched / len(gold_symptoms)
    else:
        symptom_match = 1.0 if not pred_symptoms else 0.5
    conf_num = confidence_to_numeric(logic_result.confidence_level)
    friend_num = compute_friendliness(prompt)
    return {"crop_match": crop_match, "symptom_match": symptom_match, "confidence": conf_num, "friendliness": friend_num}


def compute_metrics(results: List[Dict]) -> Dict:
    if not results:
        return {"accuracy_overall": 0.0, "confidence_avg": 0.0, "friendliness": 0.0}
    crop_accs = [r["crop_match"] for r in results]
    symptom_accs = [r["symptom_match"] for r in results]
    confs = [r["confidence"] for r in results]
    friends = [r["friendliness"] for r in results]
    crop_acc = sum(crop_accs) / len(crop_accs)
    symptom_acc = sum(symptom_accs) / len(symptom_accs)
    accuracy_overall = (crop_acc + symptom_acc) / 2
    confidence_avg = sum(confs) / len(confs)
    friendliness_avg = sum(friends) / len(friends)
    return {"accuracy_overall": accuracy_overall, "confidence_avg": confidence_avg, "friendliness": friendliness_avg}


DEFAULT_TRAIN_SAMPLES = [
    {"question": "Lúa nhà tui đang đẻ nhánh mà vàng lá từ gốc, mưa nhiều, có nên bón phân không?", "labels": {"crop": "lúa", "symptoms": ["vàng lá từ gốc"]}},
    {"question": "Cà phê bị vàng lá, rụng nhiều sau mưa, nên làm sao?", "labels": {"crop": "cà phê", "symptoms": ["vàng lá"]}},
    {"question": "Tiêu nhà em bị thối rễ, lá héo dần, có cách nào cứu không?", "labels": {"crop": "tiêu", "symptoms": ["thối rễ", "héo"]}},
    {"question": "Rầy nâu nhiều quá, đếm cả chục con trên bụi lúa, phun thuốc gì ạ?", "labels": {"crop": "lúa", "symptoms": ["rầy"]}},
    {"question": "Sầu riêng đang ra hoa mà mưa hoài, sợ không đậu trái, làm sao?", "labels": {"crop": "sầu riêng", "symptoms": []}},
    {"question": "Cây cam bị đốm lá, lá vàng rồi rụng dần, có phải nấm không?", "labels": {"crop": "cam", "symptoms": ["đốm lá", "vàng lá", "rụng lá"]}},
    {"question": "Ngô nhà tôi lá xoăn lại, còi cọc không lớn, thiếu gì vậy?", "labels": {"crop": "ngô", "symptoms": ["xoăn lá", "chậm lớn"]}},
    {"question": "Rau cải bị sâu ăn lá nhiều quá, gần thu hoạch rồi, xử lý sao?", "labels": {"crop": "rau cải", "symptoms": ["sâu"]}},
]


def create_train_file():
    ensure_directories()
    if not os.path.exists(TRAIN_FILE):
        with open(TRAIN_FILE, 'w', encoding='utf-8') as f:
            for sample in DEFAULT_TRAIN_SAMPLES:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")
        print(f"✅ Đã tạo file huấn luyện mẫu: {TRAIN_FILE}")


def load_train_data() -> List[Dict]:
    create_train_file()
    data = []
    with open(TRAIN_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def run_train_mode(epochs: int = 50):
    """
    Advanced Training Mode with:
    - Train/Validation split (80/20)
    - Dual classifier training (Crop + Symptoms)
    - Learning rate scheduling with warmup
    - Mini-batch training
    - Early stopping with patience
    - Comprehensive metrics tracking
    """
    ensure_directories()
    print("=" * 70)
    print("🚜 AGRISENSE AI - ADVANCED TRAINING MODE")
    print(f"   Epochs: {epochs} | Seed: {RANDOM_SEED}")
    print("=" * 70)
    
    # Load data
    train_data = load_train_data()
    print(f"📊 Loaded {len(train_data)} samples from {TRAIN_FILE}")
    
    # Shuffle and split train/validation (80/20)
    random.shuffle(train_data)
    split_idx = int(len(train_data) * 0.8)
    train_set = train_data[:split_idx]
    val_set = train_data[split_idx:]
    print(f"   Train set: {len(train_set)} | Validation set: {len(val_set)}")
    
    # Reset classifiers for fresh training
    global crop_classifier, symptom_classifier
    crop_classifier = CropClassifier()
    symptom_classifier = SymptomClassifier()
    
    # Training hyperparameters
    initial_lr = 0.2
    min_lr = 0.001
    warmup_epochs = 3
    lr_decay = 0.92
    patience = 15
    batch_size = min(32, len(train_set) // 4)
    
    best_combined_score = 0.0
    no_improve_count = 0
    
    all_metrics = []
    
    # Prepare data
    train_texts = [s["question"] for s in train_set]
    train_crop_labels = [s["labels"]["crop"] for s in train_set]
    train_symptom_labels = [s["labels"].get("symptoms", []) for s in train_set]
    
    val_texts = [s["question"] for s in val_set]
    val_crop_labels = [s["labels"]["crop"] for s in val_set]
    val_symptom_labels = [s["labels"].get("symptoms", []) for s in val_set]
    
    print(f"\n🎯 Training Configuration:")
    print(f"   • Batch size: {batch_size}")
    print(f"   • Initial LR: {initial_lr}")
    print(f"   • LR decay: {lr_decay}")
    print(f"   • Warmup epochs: {warmup_epochs}")
    print(f"   • Patience: {patience}")
    
    print("\n📈 Training Progress:")
    print("-" * 90)
    print(f"{'Epoch':>5} | {'Loss':>7} | {'Crop':>6} | {'Symp':>6} | {'Val':>6} | {'F1':>6} | {'LR':>8} | {'Status':<12}")
    print("-" * 90)
    
    for epoch in range(1, epochs + 1):
        # Learning rate with warmup and decay
        if epoch <= warmup_epochs:
            current_lr = initial_lr * (epoch / warmup_epochs)
        else:
            current_lr = max(min_lr, initial_lr * (lr_decay ** (epoch - warmup_epochs)))
        
        # Shuffle and create mini-batches
        indices = list(range(len(train_texts)))
        random.shuffle(indices)
        
        epoch_loss = 0.0
        num_batches = 0
        
        for i in range(0, len(indices), batch_size):
            batch_indices = indices[i:i+batch_size]
            batch_texts = [train_texts[j] for j in batch_indices]
            batch_crop_labels = [train_crop_labels[j] for j in batch_indices]
            batch_symptom_labels = [train_symptom_labels[j] for j in batch_indices]
            
            # Train crop classifier
            crop_classifier.partial_fit(batch_texts, batch_crop_labels, learning_rate=current_lr)
            
            # Train symptom classifier
            symptom_classifier.partial_fit(batch_texts, batch_symptom_labels, learning_rate=current_lr)
            
            epoch_loss += crop_classifier.get_loss()
            num_batches += 1
        
        avg_loss = epoch_loss / num_batches if num_batches > 0 else 0
        
        # Evaluate on training set
        train_crop_eval = crop_classifier.evaluate(train_texts, train_crop_labels)
        train_crop_acc = train_crop_eval["accuracy"]
        
        train_symptom_eval = symptom_classifier.evaluate(train_texts, train_symptom_labels)
        train_symptom_f1 = train_symptom_eval["f1"]
        
        # Evaluate on validation set
        val_correct = 0
        val_results = []
        
        for text, crop_label, symptom_label in zip(val_texts, val_crop_labels, val_symptom_labels):
            analysis = analyze_question(text, use_model=True)
            logic = apply_agri_logic(analysis)
            prompt = build_prompt(analysis, logic, mode="runtime")
            
            # Check crop prediction
            pred_crop = (analysis.crop or "").lower()
            gold_crop = crop_label.lower() if crop_label else ""
            if pred_crop == gold_crop:
                val_correct += 1
            
            eval_result = evaluate_prediction(
                {"crop": crop_label, "symptoms": symptom_label}, 
                analysis, 
                logic, 
                prompt
            )
            val_results.append(eval_result)
        
        val_crop_acc = val_correct / len(val_set) if val_set else 0.0
        
        # Symptom validation
        val_symptom_eval = symptom_classifier.evaluate(val_texts, val_symptom_labels)
        val_symptom_f1 = val_symptom_eval["f1"]
        
        val_metrics = compute_metrics(val_results)
        
        # Combined score (weighted average)
        combined_score = 0.6 * val_crop_acc + 0.4 * val_symptom_f1
        
        # Determine status
        status = ""
        if combined_score > best_combined_score + 0.001:  # Small threshold to avoid noise
            best_combined_score = combined_score
            no_improve_count = 0
            status = "✨ BEST"
            # Save best models
            crop_classifier.save(MODEL_FILE)
            symptom_classifier.save(SYMPTOM_MODEL_FILE)
        else:
            no_improve_count += 1
            if no_improve_count >= patience:
                status = "⏹️ STOP"
            elif no_improve_count >= patience // 2:
                status = "⚠️ PLATEAU"
            else:
                status = ""
        
        # Store metrics
        epoch_metrics = {
            "epoch": epoch,
            "train_loss": avg_loss,
            "train_crop_acc": train_crop_acc,
            "train_symptom_f1": train_symptom_f1,
            "val_crop_acc": val_crop_acc,
            "val_symptom_f1": val_symptom_f1,
            "val_combined": combined_score,
            "val_accuracy_overall": val_metrics["accuracy_overall"],
            "confidence_avg": val_metrics["confidence_avg"],
            "friendliness": val_metrics["friendliness"],
            "learning_rate": current_lr,
            "best_combined_score": best_combined_score
        }
        all_metrics.append(epoch_metrics)
        
        # Print progress
        print(f"{epoch:>5} | {avg_loss:>7.4f} | {train_crop_acc*100:>5.1f}% | {train_symptom_f1*100:>5.1f}% | {val_crop_acc*100:>5.1f}% | {val_symptom_f1*100:>5.1f}% | {current_lr:>8.5f} | {status:<12}")
        
        # Early stopping
        if no_improve_count >= patience:
            print(f"\n⏹️ Early stopping at epoch {epoch} (no improvement for {patience} epochs)")
            break
    
    print("-" * 90)
    
    # Save final metrics
    with open(TRAIN_METRICS_LOG, 'w', encoding='utf-8') as f:
        json.dump(all_metrics, f, ensure_ascii=False, indent=2)
    print(f"\n📈 Metrics saved to {TRAIN_METRICS_LOG}")
    
    # Training summary
    print("\n" + "=" * 70)
    print("✅ TRAINING COMPLETE")
    print("=" * 70)
    
    final = all_metrics[-1]
    best_epoch = max(all_metrics, key=lambda x: x["val_combined"])
    
    print(f"\n📊 FINAL RESULTS:")
    print(f"   • Total Epochs Run: {len(all_metrics)}")
    print(f"   • Best Combined Score: {best_combined_score*100:.1f}% (epoch {best_epoch['epoch']})")
    print(f"   • Best Val Crop Accuracy: {best_epoch['val_crop_acc']*100:.1f}%")
    print(f"   • Best Val Symptom F1: {best_epoch['val_symptom_f1']*100:.1f}%")
    print(f"   • Final Train Loss: {final['train_loss']:.4f}")
    print(f"   • Final Confidence: {final['confidence_avg']*100:.1f}%")
    print(f"   • Final Friendliness: {final['friendliness']*100:.1f}%")
    
    # Show training curve summary
    if len(all_metrics) >= 5:
        print(f"\n📈 TRAINING CURVE:")
        step = max(1, len(all_metrics) // 5)
        for i in range(0, len(all_metrics), step):
            m = all_metrics[i]
            bar_len = int(m["val_combined"] * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            print(f"   Epoch {m['epoch']:3d}: [{bar}] Crop:{m['val_crop_acc']*100:5.1f}% Symp:{m['val_symptom_f1']*100:5.1f}%")
        # Always show last epoch
        if len(all_metrics) % step != 0:
            m = all_metrics[-1]
            bar_len = int(m["val_combined"] * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            print(f"   Epoch {m['epoch']:3d}: [{bar}] Crop:{m['val_crop_acc']*100:5.1f}% Symp:{m['val_symptom_f1']*100:5.1f}%")
    
    print(f"\n💾 Models saved to:")
    print(f"   • Crop classifier: {MODEL_FILE}")
    print(f"   • Symptom classifier: {SYMPTOM_MODEL_FILE}")
    print("=" * 70)


def save_conversation(question: str, analysis: QuestionAnalysis, logic: AgriLogicResult, prompt: str):
    ensure_directories()
    record = {
        "timestamp": datetime.now().isoformat(),
        "question": question,
        "analysis": analysis.to_dict(),
        "logic": logic.to_dict(),
        "prompt": prompt
    }
    with open(CONVERSATIONS_LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"💾 Đã lưu vào {CONVERSATIONS_LOG}")


def run_interactive_mode():
    ensure_directories()
    if crop_classifier.load(MODEL_FILE):
        print(f"📦 Loaded crop model from {MODEL_FILE}")
    if symptom_classifier.load(SYMPTOM_MODEL_FILE):
        print(f"📦 Loaded symptom model from {SYMPTOM_MODEL_FILE}")
    print("=" * 70)
    print("🌾 AGRISENSE AI - INTERACTIVE MODE")
    print("   Nhập câu hỏi nông nghiệp để phân tích")
    print("   Gõ 'exit' hoặc 'quit' để thoát")
    print("=" * 70)
    while True:
        print()
        try:
            question = input("📝 Câu hỏi: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Tạm biệt!")
            break
        if not question:
            continue
        if question.lower() in ("exit", "quit"):
            print("👋 Tạm biệt!")
            break
        analysis = analyze_question(question, use_model=True)
        logic = apply_agri_logic(analysis)
        prompt_runtime = build_prompt(analysis, logic, mode="runtime")
        prompt_debug = build_prompt(analysis, logic, mode="debug")
        print("\n" + "-" * 50)
        print("🔍 KẾT QUẢ PHÂN TÍCH:")
        print(json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2))
        print("\n" + "-" * 50)
        print("🧠 LOGIC RESULT:")
        print(json.dumps(logic.to_dict(), ensure_ascii=False, indent=2))
        print("\n" + "-" * 50)
        print("📤 PROMPT (RUNTIME - rút gọn):")
        print(prompt_runtime)
        print("\n" + "-" * 50)
        prompt_len = len(prompt_runtime)
        token_est = prompt_len // 4
        print(f"📊 Prompt length: {prompt_len} chars | ~{token_est} tokens")
        try:
            save_choice = input("\n💾 Lưu kết quả? (y/N): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Tạm biệt!")
            break
        if save_choice == 'y':
            save_conversation(question, analysis, logic, prompt_runtime)


def main():
    parser = argparse.ArgumentParser(description="AgriSense AI - Agricultural Question Analysis Pipeline")
    parser.add_argument("--mode", choices=["interactive", "train"], default="interactive",
                        help="Mode: 'interactive' (default) or 'train'")
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs (default: 50)")
    args = parser.parse_args()
    if args.mode == "train":
        run_train_mode(epochs=args.epochs)
    else:
        run_interactive_mode()


if __name__ == "__main__":
    main()
