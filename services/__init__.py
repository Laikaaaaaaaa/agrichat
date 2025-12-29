"""
Services Package
Chứa các module xử lý chức năng của ứng dụng
"""

# Image services
from image_search import ImageSearchEngine
from image_request_handler import image_handler, is_image_request, extract_query, get_response_message
from image_intent_classifier import image_classifier
from image_search_memory import (
    image_search_memory, alternative_detector, 
    save_search_result, get_unsent_images, has_unsent_images,
    get_last_query, is_alternative_request, is_same_category_request
)

# Speech services
from speech_processor import SpeechProcessor

# News services
from news_classifier import classify_article, NewsClassifier
from rss_api import RSSNewsAPI

# Data services
from data_analyzer import AgriDataAnalyzer

# API services
from wikimedia_api import WikimediaAPI

__all__ = [
    # Image
    'ImageSearchEngine',
    'image_handler',
    'is_image_request', 
    'extract_query',
    'get_response_message',
    'image_classifier',
    'image_search_memory',
    'alternative_detector',
    'save_search_result',
    'get_unsent_images',
    'has_unsent_images',
    'get_last_query',
    'is_alternative_request',
    'is_same_category_request',
    # Speech
    'SpeechProcessor',
    # News
    'classify_article',
    'NewsClassifier',
    'RSSNewsAPI',
    # Data
    'AgriDataAnalyzer',
    # API
    'WikimediaAPI',
]
