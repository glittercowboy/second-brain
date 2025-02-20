// questions.js

document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');

    // Load any saved conversation ID from localStorage
    let currentConversationId = localStorage.getItem('conversationId') || null;

    // Auto-resize the textarea
    chatInput.style.height = '44px';
    chatInput.addEventListener('input', function() {
        this.style.height = '0';
        const contentHeight = this.scrollHeight;
        const minHeight = 44;
        this.style.height = (contentHeight > minHeight ? contentHeight : minHeight) + 'px';
    });

    // Send message on Enter (without Shift)
    chatInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    async function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;

        // Display user's message
        addMessage(message, true);
        chatInput.value = '';
        chatInput.style.height = '44px';

        // Create AI response container
        const aiMessageDiv = addMessage('', false);
        const streamSpan = aiMessageDiv.querySelector('.stream-text');

        try {
            // Build payload
            const payload = { message };
            if (currentConversationId) {
                payload.conversation_id = currentConversationId;
            }

            // Send to server
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Server error: ${response.status} - ${errorText}`);
            }

            // Get conversation ID from headers, store in localStorage
            const convId = response.headers.get('X-Conversation-Id');
            if (convId) {
                currentConversationId = convId;
                localStorage.setItem('conversationId', convId);
            }

            // Stream the response
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                const text = decoder.decode(value);
                await typeText(streamSpan, text);
            }
        } catch (error) {
            streamSpan.textContent = 'Error: ' + error.message;
            streamSpan.style.color = '#ff0000';
        }
    }

    function addMessage(text, isUser) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isUser ? 'user-message' : 'ai-message');
        if (isUser) {
            messageDiv.textContent = text;
        } else {
            const streamSpan = document.createElement('span');
            streamSpan.classList.add('stream-text');
            messageDiv.appendChild(streamSpan);
        }
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return messageDiv;
    }

    async function typeText(element, text, speed = 20) {
        for (let char of text) {
            element.textContent += char;
            chatMessages.scrollTop = chatMessages.scrollHeight;
            await new Promise(resolve => setTimeout(resolve, speed));
        }
    }
});