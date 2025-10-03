// Quản lý lịch sử chat
function showChatHistory() {
    // Lấy lịch sử chat từ backend
    pywebview.api.get_conversation_history().then(history => {
        const historyList = document.getElementById('historyList');
        historyList.innerHTML = ''; // Clear current history

        if (history.length === 0) {
            historyList.innerHTML = `
                <div class="text-center text-gray-500 py-8">
                    <i class="fas fa-inbox text-4xl mb-2"></i>
                    <p>Chưa có lịch sử chat nào</p>
                </div>
            `;
            return;
        }

        // Hiển thị từng mục trong lịch sử
        history.forEach(entry => {
            const historyItem = document.createElement('div');
            historyItem.className = 'bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow';
            historyItem.innerHTML = `
                <div class="flex justify-between items-start mb-2">
                    <span class="text-sm text-gray-500">
                        <i class="far fa-clock mr-1"></i>${entry.time}
                    </span>
                </div>
                <div class="space-y-3">
                    <div class="flex items-start gap-3">
                        <div class="flex-shrink-0">
                            <i class="fas fa-user text-blue-500"></i>
                        </div>
                        <div class="flex-grow">
                            <p class="text-gray-800">${escapeHtml(entry.user_message)}</p>
                        </div>
                    </div>
                    <div class="flex items-start gap-3">
                        <div class="flex-shrink-0">
                            <i class="fas fa-robot text-green-500"></i>
                        </div>
                        <div class="flex-grow">
                            <p class="text-gray-800 whitespace-pre-wrap">${formatAIResponse(entry.ai_response)}</p>
                        </div>
                    </div>
                </div>
            `;
            historyList.appendChild(historyItem);
        });
    });

    // Hiển thị dialog
    document.getElementById('historyDialog').classList.remove('hidden');
}

function closeHistoryDialog() {
    document.getElementById('historyDialog').classList.add('hidden');
}

function clearHistory() {
    if (confirm('Bạn có chắc muốn xóa toàn bộ lịch sử chat?')) {
        pywebview.api.clear_conversation_history().then(response => {
            showNotification('Đã xóa lịch sử chat', 'success');
            showChatHistory(); // Refresh lại dialog
        });
    }
}

function exportHistory(format) {
    pywebview.api.get_conversation_history().then(history => {
        let content = '';
        const filename = `chat-history-${new Date().toISOString().slice(0,10)}`;

        if (format === 'json') {
            content = JSON.stringify(history, null, 2);
            downloadFile(`${filename}.json`, content, 'application/json');
        } else {
            // Format as text
            content = history.map(entry => {
                return `Thời gian: ${entry.time}\n` +
                       `Người dùng: ${entry.user_message}\n` +
                       `AI: ${entry.ai_response}\n` +
                       '----------------------------------------\n';
            }).join('\n');
            downloadFile(`${filename}.txt`, content, 'text/plain');
        }
    });
}

function downloadFile(filename, content, type) {
    const blob = new Blob([content], { type: type });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();
}

function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function formatAIResponse(response) {
    // Escape HTML first
    let formatted = escapeHtml(response);
    
    // Convert markdown-style formatting
    formatted = formatted
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
        .replace(/\*(.*?)\*/g, '<em>$1</em>') // Italic
        .replace(/```(.*?)```/gs, '<pre><code>$1</code></pre>') // Code blocks
        .replace(/`([^`]+)`/g, '<code>$1</code>'); // Inline code
    
    return formatted;
}