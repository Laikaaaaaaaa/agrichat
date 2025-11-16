"""
Speech-to-Text Processor for AgriSense AI
Xử lý chuyển đổi giọng nói thành văn bản
Tối ưu hóa cho Tiếng Việt
"""

import speech_recognition as sr
import logging
from typing import Tuple, Optional
import json
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpeechProcessor:
    """
    Xử lý chuyển đổi audio input thành text
    Tối ưu hóa cho Tiếng Việt
    """
    
    def __init__(self):
        """Khởi tạo speech recognizer với cấu hình tối ưu"""
        self.recognizer = sr.Recognizer()
        
        # ✅ Tối ưu cho môi trường ồn ào
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 3000  # Giảm từ 4000 để nhạy hơn
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5
        
        # ✅ Tối ưu cho tiếng Việt - tăng phrase_time_limit
        self.recognizer.phrase_time_limit = 60  # Cho phép nói lâu hơn
        self.recognizer.non_speaking_duration = 0.3  # Giảm để detect pauses tốt hơn
        
    def recognize_from_microphone(self, language: str = 'vi-VN', timeout: int = 10) -> Tuple[bool, str]:
        """
        Ghi âm từ microphone và chuyển thành text
        
        Args:
            language (str): Mã ngôn ngữ (vi-VN cho Tiếng Việt)
            timeout (int): Thời gian chờ tối đa (giây)
        
        Returns:
            Tuple[bool, str]: (success, text/error_message)
        """
        try:
            logger.info(f"🎤 Bắt đầu ghi âm... (Timeout: {timeout}s, Ngôn ngữ: {language})")
            
            with sr.Microphone() as source:
                # ✅ Điều chỉnh cho Tiếng Việt - tăng duration
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                
                try:
                    # Ghi âm với cấu hình tối ưu
                    audio = self.recognizer.listen(
                        source, 
                        timeout=timeout, 
                        phrase_time_limit=60
                    )
                except sr.WaitTimeoutError:
                    logger.warning("⏱️ Hết thời gian chờ (timeout)")
                    return False, "Hết thời gian chờ. Vui lòng thử lại."
            
            logger.info("🎵 Đã nhận audio, đang xử lý...")
            
            # ✅ Thử multiple ngôn ngữ variants cho Tiếng Việt
            vietnamese_variants = ['vi-VN', 'vi', 'vi_VN']
            text = None
            
            for lang_variant in vietnamese_variants:
                try:
                    text = self.recognizer.recognize_google(
                        audio, 
                        language=lang_variant
                    )
                    logger.info(f"✅ Kết quả ({lang_variant}): {text}")
                    return True, text
                except sr.UnknownValueError:
                    continue
                except sr.RequestError:
                    continue
            
            if text is None:
                logger.warning("❌ Không thể hiểu giọng nói")
                return False, "Không thể hiểu giọng nói. Vui lòng nói rõ hơn."
                
        except sr.RequestError as e:
            logger.error(f"❌ Lỗi API: {e}")
            return False, f"Lỗi kết nối Google Speech API: {str(e)}"
        except Exception as e:
            logger.error(f"❌ Lỗi không mong muốn: {e}")
            return False, f"Lỗi: {str(e)}"
    
    def recognize_from_file(self, audio_file_path: str, language: str = 'vi-VN') -> Tuple[bool, str]:
        """
        Chuyển đổi file audio thành text
        
        Args:
            audio_file_path (str): Đường dẫn tới file audio
            language (str): Mã ngôn ngữ
        
        Returns:
            Tuple[bool, str]: (success, text/error_message)
        """
        try:
            if not os.path.exists(audio_file_path):
                return False, f"File không tồn tại: {audio_file_path}"
            
            logger.info(f"📂 Đang xử lý file: {audio_file_path}")
            
            with sr.AudioFile(audio_file_path) as source:
                audio = self.recognizer.record(source)
            
            logger.info("🎵 Đang chuyển đổi...")
            text = self.recognizer.recognize_google(audio, language=language)
            logger.info(f"✅ Kết quả: {text}")
            return True, text
            
        except Exception as e:
            logger.error(f"❌ Lỗi: {e}")
            return False, f"Lỗi xử lý file: {str(e)}"
    
    def get_supported_languages(self) -> dict:
        """Trả về danh sách ngôn ngữ được hỗ trợ"""
        return {
            'vi-VN': 'Tiếng Việt',
            'en-US': 'English (US)',
            'en-GB': 'English (UK)',
            'es-ES': 'Español',
            'fr-FR': 'Français',
            'de-DE': 'Deutsch',
            'zh-CN': 'Chinese Simplified',
            'zh-TW': 'Chinese Traditional',
            'ja-JP': 'Japanese',
            'ko-KR': 'Korean'
        }


if __name__ == '__main__':
    processor = SpeechProcessor()
    
    print("\n🎤 AgriSense Speech-to-Text Test")
    print("================================")
    print("Các tùy chọn:")
    print("1. Ghi âm từ microphone (Tiếng Việt)")
    print("2. Ghi âm từ microphone (English)")
    print("3. Xem ngôn ngữ được hỗ trợ")
    print("0. Thoát")
    
    while True:
        choice = input("\nChọn: ").strip()
        
        if choice == '1':
            print("\n🎤 Bắt đầu ghi âm... (nói trong 60 giây)")
            success, text = processor.recognize_from_microphone('vi-VN', timeout=60)
            if success:
                print(f"✅ Kết quả: {text}")
            else:
                print(f"❌ Lỗi: {text}")
        
        elif choice == '2':
            print("\n🎤 Bắt đầu ghi âm... (nói trong 60 giây)")
            success, text = processor.recognize_from_microphone('en-US', timeout=60)
            if success:
                print(f"✅ Kết quả: {text}")
            else:
                print(f"❌ Lỗi: {text}")
        
        elif choice == '3':
            langs = processor.get_supported_languages()
            print("\n📚 Ngôn ngữ được hỗ trợ:")
            for code, name in langs.items():
                print(f"  {code}: {name}")
        
        elif choice == '0':
            print("👋 Thoát")
            break
        
        else:
            print("❌ Lựa chọn không hợp lệ")
