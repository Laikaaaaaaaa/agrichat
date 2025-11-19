/**
 * =====================================================================
 * VoiceManager - Web Speech API Manager for AgriSense AI
 * =====================================================================
 * CHUẨN: Best Practice 2025 - Zero Repetition on Mobile
 * - Hỗ trợ tiếng Việt vi-VN
 * - Chống lặp lời trên Android Chrome
 * - Giữ nguyên smooth trên Desktop
 * =====================================================================
 */

class VoiceManager {
  constructor() {
    // ✅ Core properties
    this.recognition = null;
    this.isRunning = false;              // Guard chống start() nhiều lần
    this.isProcessing = false;           // Guard chống send nhiều lần
    this.lang = 'vi-VN';                 // Tiếng Việt
    
    // ✅ Transcript tracking
    this.finalTranscript = '';           // Lưu final results đã confirmed
    this.interimTranscript = '';         // Display real-time interim
    this.lastProcessedIndex = -1;        // Chỉ index của final result cuối cùng đã xử lý
    this.sentFinalCount = 0;             // Đếm số final results đã gửi (chống gửi lại)
    
    // ✅ Callbacks
    this.onStart = null;                 // Callback khi bắt đầu ghi âm
    this.onInterim = null;               // Callback khi có interim results (real-time display)
    this.onFinal = null;                 // Callback khi nhận final result (lâu lắm không lặp)
    this.onError = null;                 // Callback khi có lỗi
    this.onEnd = null;                   // Callback khi kết thúc ghi âm
    
    // ✅ Config
    this.config = {
      continuous: true,
      interimResults: true,
      maxAlternatives: 1,
      language: 'vi-VN'
    };
    
    // ✅ Device detection
    this.isMobile = this.detectMobile();
    
    // ✅ Initialize SpeechRecognition API
    this.initRecognition();
    
    console.log(`🎙️ VoiceManager initialized (Mobile: ${this.isMobile})`);
  }

  /**
   * Phát hiện thiết bị mobile
   */
  detectMobile() {
    return navigator.userAgentData?.mobile || 
           /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
  }

  /**
   * Khởi tạo Web Speech Recognition API
   */
  initRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      console.error('❌ Web Speech API không được hỗ trợ trên trình duyệt này');
      return false;
    }

    try {
      this.recognition = new SpeechRecognition();
      
      // ✅ Config
      this.recognition.continuous = this.config.continuous;
      this.recognition.interimResults = this.config.interimResults;
      this.recognition.maxAlternatives = this.config.maxAlternatives;
      this.recognition.lang = this.config.language;
      
      // ✅ Event handlers
      this.recognition.onstart = () => this._onStart();
      this.recognition.onresult = (event) => this._onResult(event);
      this.recognition.onerror = (event) => this._onError(event);
      this.recognition.onend = () => this._onEnd();
      
      console.log('✅ Web Speech API initialized');
      return true;
    } catch (error) {
      console.error('❌ Lỗi khởi tạo Web Speech API:', error);
      return false;
    }
  }

  /**
   * BẮT ĐẦU GHI ÂM
   * - Guard chống gọi nhiều lần
   * - Reset transcript trước mỗi session mới
   */
  start() {
    // ✅ Guard: Không start nếu đang chạy
    if (this.isRunning) {
      console.warn('⚠️ Voice recognition đang chạy rồi, bỏ qua lệnh start mới');
      return false;
    }

    // ✅ Reset trước mỗi session mới
    this.reset();
    this.isProcessing = false;

    if (!this.recognition) {
      console.error('❌ Web Speech API không khả dụng');
      return false;
    }

    try {
      this.isRunning = true;
      this.recognition.start();
      console.log('🎤 Bắt đầu ghi âm...');
      return true;
    } catch (error) {
      console.error('❌ Lỗi start voice:', error);
      this.isRunning = false;
      return false;
    }
  }

  /**
   * DỪNG GHI ÂM
   */
  stop() {
    if (!this.isRunning || !this.recognition) {
      console.warn('⚠️ Voice recognition không chạy');
      return false;
    }

    try {
      this.recognition.stop(); // Hãy dừng, không abort (tránh lỗi)
      console.log('🛑 Dừng ghi âm');
      return true;
    } catch (error) {
      console.error('❌ Lỗi stop voice:', error);
      return false;
    }
  }

  /**
   * ABORT GHI ÂM (Dừng ngay lập tức)
   */
  abort() {
    if (!this.recognition) return false;

    try {
      this.recognition.abort();
      this.isRunning = false;
      console.log('⏹️ Abort voice');
      return true;
    } catch (error) {
      console.error('❌ Lỗi abort voice:', error);
      return false;
    }
  }

  /**
   * RESET TRANSCRIPT
   */
  reset() {
    this.finalTranscript = '';
    this.interimTranscript = '';
    this.lastProcessedIndex = -1;
    this.sentFinalCount = 0;
    console.log('🔄 Reset transcript');
  }

  /**
   * ========== EVENT HANDLERS ==========
   */

  /**
   * Callback khi bắt đầu ghi âm
   */
  _onStart() {
    console.log('🎤 onstart triggered');
    if (this.onStart) {
      this.onStart();
    }
  }

  /**
   * Callback khi nhận results
   * 
   * CORE LOGIC CHỐNG LẶP LỜI:
   * 1. Chỉ process final results (isFinal === true)
   * 2. Track lastProcessedIndex để không process result cũ 2 lần
   * 3. Chỉ gửi 1 lần duy nhất khi nhận final result mới
   * 4. Interim: Chỉ display, không gửi
   */
  _onResult(event) {
    let newFinalAdded = false;
    
    // ✅ Process final results
    for (let i = this.lastProcessedIndex + 1; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      
      if (event.results[i].isFinal) {
        // ✅ FINAL RESULT - Đây là kết quả xác nhận từ API
        this.finalTranscript += transcript + ' ';
        this.lastProcessedIndex = i;
        newFinalAdded = true;
        
        console.log(`✅ New FINAL result [${i}]: "${transcript}"`);
      }
    }
    
    // ✅ Xây dựng interim display
    this.interimTranscript = '';
    
    if (this.isMobile) {
      // 📱 Mobile: Chỉ lấy interim từ result cuối cùng (tránh accumulate)
      if (event.results.length > 0) {
        const lastResult = event.results[event.results.length - 1];
        if (!lastResult.isFinal) {
          this.interimTranscript = lastResult[0].transcript;
        }
      }
    } else {
      // 💻 Desktop: Accumulate interim từ tất cả results sau final cuối cùng
      for (let i = this.lastProcessedIndex + 1; i < event.results.length; i++) {
        if (!event.results[i].isFinal) {
          this.interimTranscript += event.results[i][0].transcript;
        }
      }
    }
    
    // ✅ Callback: Hiển thị real-time interim (không gửi)
    if (this.onInterim) {
      const displayText = (this.finalTranscript + this.interimTranscript).trim();
      this.onInterim(displayText);
    }
    
    // ✅ Callback: Gửi final result MỘT LẦN DUY NHẤT (chống lặp lời)
    if (newFinalAdded && !this.isProcessing) {
      this.isProcessing = true;
      this.sentFinalCount++;
      
      console.log(`🚀 Sending FINAL result #${this.sentFinalCount}:`, this.finalTranscript.trim());
      
      if (this.onFinal) {
        this.onFinal(this.finalTranscript.trim());
      }
    }
    
    console.log(`📊 Results: ${event.results.length}, Final count: ${this.sentFinalCount}, Interim: "${this.interimTranscript}"`);
  }

  /**
   * Callback khi có lỗi
   */
  _onError(event) {
    console.error(`❌ Speech recognition error: ${event.error}`);
    
    let errorMsg = 'Lỗi nhận dạng giọng nói';
    
    switch (event.error) {
      case 'network':
        errorMsg = '❌ Lỗi kết nối mạng - Kiểm tra internet';
        break;
      case 'audio-capture':
        errorMsg = '❌ Không thể truy cập microphone - Kiểm tra quyền';
        break;
      case 'not-allowed':
        errorMsg = '❌ Bạn đã từ chối quyền microphone';
        break;
      case 'no-speech':
        errorMsg = '❌ Không phát hiện giọng nói - Thử lại';
        break;
      case 'network-timeout':
        errorMsg = '⏱️ Hết thời gian chờ - Thử lại';
        break;
      case 'service-not-available':
        errorMsg = '⚠️ Dịch vụ Speech Recognition không khả dụng';
        break;
      default:
        errorMsg = `❌ Lỗi: ${event.error}`;
    }
    
    if (this.onError) {
      this.onError(errorMsg);
    }
  }

  /**
   * Callback khi kết thúc ghi âm
   * 
   * CRITICAL: Không auto-start lại (tránh infinite loop trên mobile)
   * Chỉ stop flag running, user phải bấm button để start lại
   */
  _onEnd() {
    console.log('🔔 onend triggered');
    this.isRunning = false;
    this.isProcessing = false;
    
    console.log(`📝 Session kết thúc - Final count: ${this.sentFinalCount}`);
    
    // ⚠️ QUAN TRỌNG: KHÔNG gọi recognition.start() ở đây
    // (tránh infinite loop trên mobile)
    
    if (this.onEnd) {
      this.onEnd();
    }
  }

  /**
   * ========== UTILITY METHODS ==========
   */

  /**
   * Get current display text
   */
  getDisplayText() {
    return (this.finalTranscript + this.interimTranscript).trim();
  }

  /**
   * Get final transcript only
   */
  getFinalText() {
    return this.finalTranscript.trim();
  }

  /**
   * Kiểm tra xem SpeechRecognition đang chạy không
   */
  isActive() {
    return this.isRunning;
  }

  /**
   * Cấu hình ngôn ngữ
   */
  setLanguage(lang) {
    this.config.language = lang;
    if (this.recognition) {
      this.recognition.lang = lang;
    }
  }

  /**
   * Toggle ghi âm (Press & Hold hoặc nhấp lần 1 để bật, lần 2 để tắt)
   */
  toggle() {
    if (this.isRunning) {
      return this.stop();
    } else {
      return this.start();
    }
  }

  /**
   * Lấy thông tin voice status
   */
  getStatus() {
    return {
      running: this.isRunning,
      processing: this.isProcessing,
      isMobile: this.isMobile,
      finalCount: this.sentFinalCount,
      finalText: this.getFinalText(),
      displayText: this.getDisplayText()
    };
  }
}

// ✅ Export để dùng trong các file khác
if (typeof module !== 'undefined' && module.exports) {
  module.exports = VoiceManager;
}

console.log('✅ VoiceManager.js loaded');
