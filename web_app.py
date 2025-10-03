from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import base64
import io
import re
import requests
import time
import random
import logging
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv
from image_search import ImageSearchEngine
from modes import ModeManager
from model_config import get_model_config

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

HERE = os.path.dirname(os.path.abspath(__file__))

# Tạo Flask app
app = Flask(__name__, template_folder=HERE, static_folder=HERE)

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
        logging.info("Khởi tạo hoàn tất!")

        # Setup API keys từ biến môi trường
        raw_gemini_keys = os.getenv('GEMINI_API_KEYS')
        if raw_gemini_keys:
            self.gemini_api_keys = [key.strip() for key in re.split(r'[\s,;]+', raw_gemini_keys) if key.strip()]
        else:
            single_key = os.getenv('GEMINI_API_KEY', '').strip()
            self.gemini_api_keys = [single_key] if single_key else []

        if not self.gemini_api_keys:
            logging.warning("⚠️  Không tìm thấy GEMINI_API_KEYS hoặc GEMINI_API_KEY. Vui lòng cấu hình .env.")

        self.current_key_index = 0
        
        # Geography prompt for domain expertise
        self.geography_prompt = """
Bạn là chuyên gia AI nông nghiệp thông minh AgriSense AI với:
- Kiến thức sâu về nông nghiệp, chăn nuôi, thủy sản Việt Nam và quốc tế
- Hiểu biết về công nghệ smart farming, IoT, cảm biến nông nghiệp
- Kinh nghiệm tư vấn canh tác, quản lý dịch bệnh, thời vụ
- Khả năng phân tích hình ảnh cây trồng, vật nuôi, đất đai

NHIỆM VỤ CHÍNH:
✅ Tư vấn kỹ thuật nông nghiệp chuyên sâu
✅ Nhận diện bệnh tật cây trồng/vật nuôi qua hình ảnh  
✅ Đưa ra giải pháp canh tác hiệu quả
✅ Cung cấp thông tin thị trường nông sản
✅ Hướng dẫn sử dụng công nghệ thông minh

PHONG CÁCH TRẢ LỜI:
- Chuyên nghiệp nhưng thân thiện, dễ hiểu
- Ưu tiên giải pháp thực tế, khả thi
- Đưa ra số liệu cụ thể khi có thể
- Tương tác bằng tiếng Việt tự nhiên
"""
        
        # Log initial setup
        logging.info(f"Gemini API Keys: {len(self.gemini_api_keys)} khóa")
        
        # Configure Gemini API with first key
        if self.gemini_api_keys:
            try:
                genai.configure(api_key=self.gemini_api_keys[self.current_key_index])
                logging.info(f"Đã cấu hình Gemini API với khóa #{self.current_key_index + 1}")
            except Exception as e:
                logging.error(f"Lỗi cấu hình Gemini API: {e}")
        else:
            logging.error("❌ Không có API key Gemini để cấu hình.")

    def generate_content_with_fallback(self, prompt, image_data=None):
        """Generate content with API key fallback"""
        max_attempts = len(self.gemini_api_keys)
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                model_config = get_model_config()
                model = genai.GenerativeModel(
                    model_name=model_config['model'],
                    generation_config=model_config['generation_config'],
                    safety_settings=model_config['safety_settings']
                )
                
                if image_data:
                    # Handle image + text input
                    content = [prompt, image_data]
                    response = model.generate_content(content)
                else:
                    # Handle text-only input
                    response = model.generate_content(prompt)
                
                return response
                
            except Exception as gen_error:
                last_exception = gen_error
                error_message = str(gen_error).lower()
                
                if any(quota_keyword in error_message for quota_keyword in 
                       ['quota', 'rate limit', 'too many requests', 'resource_exhausted']):
                    logging.warning(f"API key #{self.current_key_index + 1} hết quota, chuyển sang key tiếp theo...")
                    if not self.get_next_gemini_key():
                        logging.error("Tất cả API keys đã hết quota!")
                        break
                    continue
                else:
                    logging.error(f"Lỗi không xử lý được: {error_message}")
                    raise gen_error

        # If all keys failed, raise the last error with the last exception
        raise Exception(f"Tất cả {max_attempts} lần thử API keys thất bại. Lỗi cuối: {last_exception}")

    def chat(self, message, image_data=None):
        """
        Main chat method for Flask API
        """
        try:
            # Kiểm tra lệnh đặc biệt để xóa trí nhớ
            if message.lower().strip() in ['xóa lịch sử', 'reset', 'clear memory', 'xoa lich su']:
                return self.clear_conversation_history()
            
            # Kiểm tra lệnh để xem lịch sử
            if message.lower().strip() in ['xem lịch sử', 'lịch sử', 'lich su', 'show history', 'history']:
                return self.show_conversation_history()
            
            # Lấy ngữ cảnh từ lịch sử hội thoại
            conversation_context = self.get_conversation_context()

            # Lấy system prompt theo chế độ hiện tại
            try:
                mode_system_prompt = self.mode_manager.get_system_prompt() or ''
            except Exception:
                mode_system_prompt = ''

            # Tạo prompt với ngữ cảnh
            enhanced_prompt = f"""{mode_system_prompt}

{self.geography_prompt}

{conversation_context}

HƯỚNG DẪN QUAN TRỌNG:
- Hãy tham khảo lịch sử hội thoại ở trên để hiểu ngữ cảnh
- Nếu câu hỏi hiện tại liên quan đến cuộc hội thoại trước, hãy kết nối thông tin
- Ví dụ: nếu trước đó nói về "cây xoài" và bây giờ hỏi "chó", hãy trả lời về chó nhưng có thể đề cập "khác với cây xoài vừa nói..."
- Nếu không liên quan, trả lời bình thường

Câu hỏi hiện tại: {message}"""
            
            # Generate AI response với ngữ cảnh
            response = self.generate_content_with_fallback(enhanced_prompt, image_data)
            ai_response = response.text
            
            # Lưu cuộc hội thoại vào trí nhớ
            self.add_to_conversation_history(message, ai_response)
            
            return {"response": ai_response, "success": True}
            
        except Exception as e:
            error_response = f"Xin lỗi, có lỗi xảy ra: {str(e)}"
            # Vẫn lưu vào lịch sử để theo dõi
            self.add_to_conversation_history(message, error_response)
            return {"response": error_response, "success": False}

    def add_to_conversation_history(self, user_message, ai_response):
        """Thêm cuộc hội thoại vào trí nhớ ngắn hạn"""
        conversation_item = {
            'timestamp': time.time(),
            'user': user_message,
            'ai': ai_response
        }
        
        self.conversation_history.append(conversation_item)
        
        # Giới hạn số lượng cuộc hội thoại lưu trữ
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history.pop(0)
        
        logging.info(f"Đã lưu cuộc hội thoại. Tổng: {len(self.conversation_history)}")

    def get_conversation_context(self):
        """Lấy ngữ cảnh từ lịch sử hội thoại"""
        if not self.conversation_history:
            return "Đây là cuộc hội thoại đầu tiên."
        
        context = "LỊCH SỬ HỘI THOẠI GẦN ĐÂY:\n"
        for i, conv in enumerate(self.conversation_history[-5:], 1):  # Chỉ lấy 5 cuộc hội thoại gần nhất
            context += f"\n[Hội thoại {i}]\n"
            context += f"Người dùng: {conv['user']}\n"
            context += f"AI: {conv['ai'][:200]}{'...' if len(conv['ai']) > 200 else ''}\n"
        
        return context

    def clear_conversation_history(self):
        """Xóa lịch sử hội thoại"""
        self.conversation_history.clear()
        return "✅ Đã xóa lịch sử hội thoại. Bắt đầu cuộc trò chuyện mới!"

    def show_conversation_history(self):
        """Hiển thị lịch sử hội thoại"""
        if not self.conversation_history:
            return "📝 Chưa có lịch sử hội thoại nào."
        
        history_text = f"📚 LỊCH SỬ HỘI THOẠI ({len(self.conversation_history)} cuộc):\n\n"
        for i, conv in enumerate(self.conversation_history, 1):
            timestamp = time.strftime('%H:%M:%S', time.localtime(conv['timestamp']))
            history_text += f"[{i}] {timestamp}\n"
            history_text += f"👤 Bạn: {conv['user']}\n"
            history_text += f"🤖 AI: {conv['ai'][:100]}{'...' if len(conv['ai']) > 100 else ''}\n\n"
        
        return history_text

    def get_next_gemini_key(self):
        """Chuyển sang API key Gemini tiếp theo khi gặp lỗi"""
        if len(self.gemini_api_keys) <= 1:
            return False
            
        self.current_key_index = (self.current_key_index + 1) % len(self.gemini_api_keys)
        try:
            genai.configure(api_key=self.gemini_api_keys[self.current_key_index])
            logging.info(f"Đã chuyển sang Gemini API key #{self.current_key_index + 1}")
            return True
        except Exception as e:
            logging.error(f"Lỗi khi chuyển API key Gemini: {e}")
            return False

    def enhance_prompt_for_mode(self, prompt, image_data=None):
        """Enhance prompt based on current mode"""
        return self.mode_manager.enhance_prompt(prompt, image_data)

    def get_weather_info(self):
        """Lấy thông tin thời tiết từ API"""
        try:
            # Simple weather API call - you can integrate with a weather service
            return {
                "success": True,
                "temp": "28",
                "condition": "Nắng ít mây",
                "city": "Hồ Chí Minh",
                "country": "Việt Nam"
            }
        except Exception as e:
            logging.error(f"Lỗi lấy thông tin thời tiết: {e}")
            return {"success": False, "message": "Không thể lấy dữ liệu thời tiết"}

# Khởi tạo API instance
api_instance = Api()

@app.route('/')
def index():
    """Trang chủ"""
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory(HERE, filename)

@app.route('/js/<path:filename>')
def js_files(filename):
    """Serve JS files"""
    return send_from_directory(os.path.join(HERE, 'js'), filename)

@app.route('/templates/<path:filename>')
def template_files(filename):
    """Serve template files"""
    return send_from_directory(os.path.join(HERE, 'templates'), filename)

@app.route('/api/chat', methods=['POST'])
def chat():
    """API endpoint for chat"""
    try:
        data = request.json
        message = data.get('message', '')
        image_data = data.get('image_data')
        
        # Process message through API
        response = api_instance.chat(message, image_data)
        return jsonify(response)
    except Exception as e:
        logging.error(f"Lỗi chat API: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/weather', methods=['GET'])
def weather():
    """API endpoint for weather"""
    try:
        weather_data = api_instance.get_weather_info()
        return jsonify(weather_data)
    except Exception as e:
        logging.error(f"Lỗi weather API: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Khởi động AgriSense AI Web Server...")
    print("📡 Server đang chạy tại: http://localhost:5000")
    print("🌐 Mở trình duyệt và truy cập: http://localhost:5000")
    print("⭐ Nhấn Ctrl+C để dừng server")
    
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True,
        use_reloader=False  # Tránh restart khi debug
    )