/**
 * HƯỚNG DẪN INTEGRATE VoiceManager VÀO index.html
 * ================================================================
 * 
 * BƯỚC 1: Thêm script tag trong <head> hoặc trước closing </body>
 * ================================================================
 * 
 * <script src="VoiceManager.js"></script>
 * 
 * 
 * BƯỚC 2: Khởi tạo VoiceManager trong index.html
 * ================================================================
 * 
 * // Khởi tạo VoiceManager
 * const voiceManager = new VoiceManager();
 * 
 * // Thiết lập callbacks
 * voiceManager.onStart = () => {
 *   console.log('🎤 Bắt đầu ghi âm');
 *   voiceBtn.classList.add('recording');
 * };
 * 
 * voiceManager.onInterim = (text) => {
 *   // Hiển thị real-time interim results
 *   messageInput.value = text;
 *   messageInput.scrollLeft = messageInput.scrollWidth;
 * };
 * 
 * voiceManager.onFinal = (finalText) => {
 *   // Gửi final results (CHỈ GỌI 1 LẦN DUY NHẤT cho mỗi câu)
 *   console.log('✅ Final text:', finalText);
 *   messageInput.value = finalText;
 *   
 *   // Tự động gửi hoặc để user bấm send
 *   // sendMessage(); // Nếu muốn auto-send
 * };
 * 
 * voiceManager.onError = (errorMsg) => {
 *   console.error('❌', errorMsg);
 *   alert(errorMsg);
 * };
 * 
 * voiceManager.onEnd = () => {
 *   console.log('🛑 Kết thúc ghi âm');
 *   voiceBtn.classList.remove('recording');
 * };
 * 
 * 
 * BƯỚC 3: Gắn sự kiện vào nút voice button
 * ================================================================
 * 
 * // Nút toggle (press & hold hoặc click to start/stop)
 * voiceBtn.addEventListener('click', () => {
 *   voiceManager.toggle();
 * });
 * 
 * // Hoặc Press & Hold (mousedown = start, mouseup = stop)
 * voiceBtn.addEventListener('mousedown', () => {
 *   voiceManager.start();
 * });
 * 
 * voiceBtn.addEventListener('mouseup', () => {
 *   voiceManager.stop();
 * });
 * 
 * voiceBtn.addEventListener('touchstart', (e) => {
 *   e.preventDefault();
 *   voiceManager.start();
 * });
 * 
 * voiceBtn.addEventListener('touchend', (e) => {
 *   e.preventDefault();
 *   voiceManager.stop();
 * });
 * 
 * 
 * BƯỚC 4: Dọn dẹp khi page unload
 * ================================================================
 * 
 * window.addEventListener('beforeunload', () => {
 *   if (voiceManager.isActive()) {
 *     voiceManager.abort();
 *   }
 * });
 * 
 * 
 * ĐẶC ĐIỂM:
 * ================================================================
 * 
 * ✅ KHÔNG LẶP LỜI trên mobile (rebuild finals, tracking index)
 * ✅ Chống restart vô hạn (isRunning guard)
 * ✅ Gửi 1 lần duy nhất cho mỗi final result (sentFinalCount tracking)
 * ✅ Mobile-optimized interim (chỉ hiển thị result cuối cùng)
 * ✅ Desktop smooth (accumulate all interim)
 * ✅ Tiếng Việt vi-VN support
 * ✅ Chi tiết console logs để debug
 * ✅ Clean error handling
 * ✅ Press & Hold hoặc toggle mode
 * 
 * 
 * DEBUG COMMANDS (dùng trong console):
 * ================================================================
 * 
 * // Kiểm tra status
 * voiceManager.getStatus()
 * 
 * // Lấy display text
 * voiceManager.getDisplayText()
 * 
 * // Lấy final text
 * voiceManager.getFinalText()
 * 
 * // Kiểm tra đang chạy không
 * voiceManager.isActive()
 * 
 * // Reset manual
 * voiceManager.reset()
 * 
 * // Thay đổi ngôn ngữ
 * voiceManager.setLanguage('en-US')
 * 
 */
