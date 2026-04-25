// chat.js - AI 聊天机器人

let conversationId = null;

function toggleChat() {
    const widget = document.getElementById('chat-widget');
    widget.classList.toggle('collapsed');

    const icon = document.getElementById('chat-toggle-icon');
    if (widget.classList.contains('collapsed')) {
        icon.classList.remove('bi-chevron-up');
        icon.classList.add('bi-chevron-down');
    } else {
        icon.classList.remove('bi-chevron-down');
        icon.classList.add('bi-chevron-up');
        // 聚焦输入框
        document.getElementById('chat-input').focus();
    }
}

function openChat() {
    const widget = document.getElementById('chat-widget');
    widget.classList.remove('collapsed');
    document.getElementById('chat-input').focus();
}

function handleChatKeypress(event) {
    if (event.key === 'Enter') {
        sendChat();
    }
}

function sendChat() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();

    if (!message) return;

    // 添加用户消息
    addMessage('user', message);
    input.value = '';

    // 发送请求
    fetch('/api/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            message: message,
            conversation_id: conversationId
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) {
            addMessage('bot', '抱歉，AI 服务暂时不可用。请稍后再试。');
        } else {
            addMessage('bot', data.answer);
            if (data.conversation_id) {
                conversationId = data.conversation_id;
            }
        }
    })
    .catch(err => {
        console.error('Chat error:', err);
        addMessage('bot', '抱歉，网络连接出现问题。请稍后再试。');
    });
}

function addMessage(role, content) {
    const messagesDiv = document.getElementById('chat-messages');

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message ' + role;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;

    messageDiv.appendChild(contentDiv);
    messagesDiv.appendChild(messageDiv);

    // 滚动到底部
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// 预置问题快速提问
const quickQuestions = [
    '有什么推荐的降噪耳机？',
    '索尼 WH-1000XM5 多少钱？',
    '耳机怎么连接蓝牙？',
    '支持退货吗？'
];
