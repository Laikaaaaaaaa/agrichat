// Khởi tạo lịch sử chat trong localStorage nếu chưa có
if (!localStorage.getItem('chatHistory')) {
    localStorage.setItem('chatHistory', JSON.stringify([]));
}

// Hàm lấy timestamp hiện tại
function getCurrentTimestamp() {
    return new Date().toISOString();
}

// Hàm lưu tin nhắn vào lịch sử
function saveToHistory(sender, content) {
    const history = JSON.parse(localStorage.getItem('chatHistory') || '[]');
    const timestamp = getCurrentTimestamp();
    
    // Kiểm tra xem có phiên chat nào trong hôm nay chưa
    const today = new Date().toLocaleDateString();
    let currentSession = history.find(session => 
        new Date(session.timestamp).toLocaleDateString() === today
    );

    if (!currentSession) {
        currentSession = {
            timestamp: timestamp,
            messages: []
        };
        history.push(currentSession);
    }

    // Thêm tin nhắn mới vào phiên hiện tại
    currentSession.messages.push({
        sender,
        content,
        timestamp
    });

    // Giới hạn số lượng phiên chat lưu trữ (ví dụ: 50 phiên gần nhất)
    if (history.length > 50) {
        history.shift();
    }

    localStorage.setItem('chatHistory', JSON.stringify(history));
}

// Hàm tạo hiệu ứng typing cho bot
async function typeMessage(element, text, speed = 30) {
    let index = 0;
    element.innerHTML = ''; // Clear existing content

    function typeNextChar() {
        if (index < text.length) {
            if (text.substring(index).startsWith('![')) {
                // Tìm vị trí kết thúc của markdown image
                const endIndex = text.indexOf(')', index);
                if (endIndex !== -1) {
                    element.innerHTML += text.substring(index, endIndex + 1);
                    index = endIndex + 1;
                }
            } else if (text.substring(index).startsWith('<img')) {
                // Tìm vị trí kết thúc của HTML image tag
                const endIndex = text.indexOf('>', index);
                if (endIndex !== -1) {
                    element.innerHTML += text.substring(index, endIndex + 1);
                    index = endIndex + 1;
                }
            } else if (text.substring(index).startsWith('```')) {
                // Xử lý code block
                const endIndex = text.indexOf('```', index + 3);
                if (endIndex !== -1) {
                    element.innerHTML += text.substring(index, endIndex + 3);
                    index = endIndex + 3;
                }
            } else {
                element.innerHTML += text[index];
                index++;
            }
            
            // Scroll to bottom
            const chatContainer = document.querySelector('.chat-container');
            chatContainer.scrollTop = chatContainer.scrollHeight;
            
            setTimeout(typeNextChar, speed);
        }
    }

    typeNextChar();
}

// Override hàm appendMessage để thêm hiệu ứng typing và lưu lịch sử
window.appendMessage = function(sender, message) {
    const chatContainer = document.querySelector('.chat-container');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    const timestamp = new Date().toLocaleTimeString();
    const header = document.createElement('div');
    header.className = 'flex justify-between items-center mb-1';
    header.innerHTML = `
        <span class="text-sm text-gray-500">${sender === 'user' ? 'Bạn' : 'AgriSense AI'}</span>
        <span class="text-xs text-gray-400">${timestamp}</span>
    `;
    
    const content = document.createElement('div');
    content.className = 'text-gray-800';
    
    messageDiv.appendChild(header);
    messageDiv.appendChild(content);
    chatContainer.appendChild(messageDiv);
    
    if (sender === 'bot') {
        // Thêm hiệu ứng typing cho bot
        typeMessage(content, message);
    } else {
        content.innerHTML = message;
    }
    
    // Lưu vào lịch sử
    saveToHistory(sender, message);
    
    // Scroll to bottom
    chatContainer.scrollTop = chatContainer.scrollHeight;
};