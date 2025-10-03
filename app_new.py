import webview
import threading
import os
import base64
import io
import re
import requests
import time
import random
import logging
from PIL import Image
from dotenv import load_dotenv
from image_search import ImageSearchEngine  
from modes import ModeManager  
from gemini_initializer import GeminiInitializer

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

HERE = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(HERE, 'index.html')

class Api:
    def __init__(self):
        logging.info("Khởi tạo AgriSense AI API...")
        load_dotenv()
        
        # Initialize Mode Manager
        logging.info("Khởi tạo Mode Manager...")
        self.mode_manager = ModeManager()
        
        # Initialize Image Search Engine
        logging.info("Khởi tạo Image Search Engine...")
        self.image_engine = ImageSearchEngine()
        
        # Initialize Short-term Memory (lưu trữ 10 cuộc hội thoại gần nhất)
        self.conversation_history = []
        self.max_history_length = 10
        
        # Initialize Gemini
        logging.info("Khởi tạo Gemini Model...")
        self.gemini = GeminiInitializer()
        if not self.gemini.initialize_gemini_model():
            logging.error("❌ Không thể khởi tạo Gemini model!")
        else:
            logging.info("✅ Khởi tạo Gemini thành công!")
        
        logging.info("Khởi tạo hoàn tất!")
        
        self.geography_prompt = """
Bạn là AgriSense AI - Chuyên gia tư vấn nông nghiệp thông minh. Bạn có khả năng cung cấp thông tin và giải đáp thắc mắc liên quan đến nông nghiệp, bao gồm nhưng không giới hạn ở các chủ đề như cây trồng, vật nuôi, thời tiết, thị trường nông sản và các vấn đề nông nghiệp khác. Hãy cung cấp thông tin chính xác và hữu ích nhất có thể.
"""
        
        self.image_analysis_prompt = """
Bạn là AgriSense AI - Chuyên gia phân tích hình ảnh nông nghiệp. Hãy phân tích hình ảnh một cách chi tiết và chuyên nghiệp:

**Nếu là hình ảnh đất:**
- Phân tích (Phân tích theo yêu cầu nếu có)
- Đánh giá chất lượng đất (màu sắc, độ ẩm, kết cấu)
- Phân tích loại đất và độ pH có thể
- Gợi ý cây trồng phù hợp
- Khuyến nghị cách cải thiện đất

**Nếu là hình ảnh cây trồng:**
- Nhận dạng loại cây/giống cây
- Đánh giá tình trạng sức khỏe
- Phát hiện dấu hiệu bệnh tật, sâu hại
- Gợi ý biện pháp chăm sóc/điều trị

**Nếu là hình ảnh khác liên quan nông nghiệp:**
- Mô tả những gì bạn thấy
- Đưa ra lời khuyên chuyên môn liên quan

Hãy trả lời bằng tiếng Việt, cụ thể và chi tiết.
"""
        
        # Unsplash API endpoint (free tier)
        self.unsplash_api_url = "https://api.unsplash.com/search/photos"