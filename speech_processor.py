"""
Speech-to-Text Processor for AgriSense AI
Xử lý chuyển đổi giọng nói thành văn bản
Tối ưu hóa cho Tiếng Việt
✅ Enhanced: Word repetition filtering + Mobile optimization
"""

import speech_recognition as sr
import logging
from typing import Tuple, Optional, List
import json
import os
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpeechProcessor:
    """
    Xử lý chuyển đổi audio input thành text
    Tối ưu hóa cho Tiếng Việt + Lọc lặp từ + Tối ưu mobile
    """
    
    def __init__(self):
        """Khởi tạo speech recognizer với cấu hình tối ưu"""
        self.recognizer = sr.Recognizer()
        
        # ✅ Tối ưu cho môi trường ồn ào (Mobile + Desktop)
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 3000  # Tối ưu cho mobile
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5
        
        # ✅ Tối ưu cho tiếng Việt - tăng phrase_time_limit
        self.recognizer.phrase_time_limit = 60  # Cho phép nói lâu hơn
        self.recognizer.non_speaking_duration = 0.3  # Giảm để detect pauses tốt hơn
        
        # ✅ Vietnamese stopwords for duplicate filtering
        self.vietnamese_stopwords = {
            'à', 'ạ', 'ai', 'an', 'à', 'anh', 'ba', 'bác', 'bạn', 'bị', 'bởi',
            'cả', 'các', 'cánh', 'có', 'cô', 'cơ', 'cùng', 'cuộc', 'cái',
            'da', 'dã', 'đã', 'đại', 'đâu', 'để', 'đi', 'được', 'đó', 'đội',
            'em', 'ếu', 'ệu', 'e',
            'gì', 'giai', 'gần', 'gây',
            'hà', 'hại', 'hầu', 'hơn', 'hư', 'hủy',
            'ích', 'lại', 'làm', 'là', 'lấy', 'lên', 'lẻ', 'lết', 'lô',
            'mà', 'man', 'mặt', 'một', 'mới', 'mục', 'mỹ',
            'nà', 'này', 'nên', 'nếu', 'như', 'người', 'nhu', 'nó', 'nơi', 'nữa',
            'ở', 'ông', 'ông', 'ơi',
            'phải', 'phía', 'phục',
            'quá', 'quanh', 'quân', 'quế', 'quý',
            'rằng', 'rất', 'rồi', 'rõ', 'ru',
            'sách', 'sai', 'sau', 'sáy', 'sếp', 'sinh', 'số', 'su',
            'tà', 'tại', 'tam', 'tập', 'tất', 'tầng', 'tầu', 'tế', 'thách', 'thành',
            'thấy', 'thế', 'thêm', 'theo', 'thích', 'thieu', 'thông', 'thì',
            'ti', 'tính', 'tò', 'tờ', 'tối', 'tôi', 'trăng', 'trước', 'trừ',
            'từ', 'từng', 'tương', 'tự',
            'và', 'văn', 'vậy', 'vé', 'vẽ', 'về', 'vì', 'việc', 'viên', 'vô',
            'vu', 'vụ', 'vui', 'vừa',
            'xa', 'xảy', 'xây', 'xin', 'xinh', 'xong', 'xử',
            'yêu',
            'ý', 'yên'
        }
        
    def remove_word_repetition(self, text: str, min_confidence: float = 0.6) -> str:
        """
        ✅ Xóa lặp từ trong kết quả nhận dạng
        Giải quyết vấn đề "lặp từ" khi nói trên mobile
        
        Args:
            text (str): Text input từ speech recognition
            min_confidence (float): Ngưỡng confidence tối thiểu
        
        Returns:
            str: Text đã xóa lặp từ
        """
        if not text or not isinstance(text, str):
            return text
        
        # ✅ Xóa khoảng trắng thừa
        text = ' '.join(text.split())
        
        # ✅ Tách từ
        words = text.lower().split()
        if not words:
            return text
        
        # ✅ Lọc lặp từ liên tiếp
        filtered_words = [words[0]]
        for i in range(1, len(words)):
            current = words[i]
            prev = words[i-1]
            
            # ✅ Không thêm từ nếu nó giống từ trước (loại bỏ lặp liên tiếp)
            if current != prev:
                filtered_words.append(current)
            else:
                logger.info(f"🔁 Lọc từ lặp: '{current}'")
        
        # ✅ Xóa các "um", "ơi", "ní" lặp nhiều lần (artifacts)
        filler_words = ['um', 'ơi', 'ní', 'nữa', 'cái', 'ạ', 'ơi', 'nhé', 'hả']
        result_words = []
        for i, word in enumerate(filtered_words):
            if word in filler_words:
                # Chỉ giữ nếu từ trước khác filler
                if i == 0 or result_words[-1] not in filler_words:
                    result_words.append(word)
            else:
                result_words.append(word)
        
        result = ' '.join(result_words)
        
        # ✅ Khôi phục casing gốc (nếu input là title case)
        if text and text[0].isupper():
            result = result[0].upper() + result[1:] if len(result) > 1 else result.upper()
        
        logger.info(f"✅ Cleaned: '{text}' → '{result}'")
        return result
    
    def filter_consecutive_duplicates(self, words_list: List[str], max_consecutive: int = 1) -> List[str]:
        """
        ✅ Lọc nhiều từ lặp liên tiếp
        
        Args:
            words_list: Danh sách từ
            max_consecutive: Số lần lặp tối đa (mặc định = 1, không lặp)
        
        Returns:
            Danh sách từ đã lọc
        """
        if not words_list:
            return []
        
        filtered = [words_list[0]]
        consecutive_count = 1
        
        for i in range(1, len(words_list)):
            if words_list[i] == words_list[i-1]:
                consecutive_count += 1
                if consecutive_count <= max_consecutive:
                    filtered.append(words_list[i])
            else:
                filtered.append(words_list[i])
                consecutive_count = 1
        
        return filtered
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
        ✅ Áp dụng lọc lặp từ tự động
        
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
            
            # ✅ Áp dụng lọc lặp từ
            cleaned_text = self.remove_word_repetition(text)
            
            logger.info(f"✅ Kết quả: {cleaned_text}")
            return True, cleaned_text
            
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
