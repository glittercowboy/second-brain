document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');

    // Auto-resize textarea as user types
    chatInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    // Send message when Enter is pressed (without Shift)
    chatInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Send message when button is clicked
    sendButton.addEventListener('click', sendMessage);

    function addMessage(text, isUser = false) {
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

    async function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;

        console.log('Sending message:', message);

        // Add user message
        addMessage(message, true);
        
        // Clear input
        chatInput.value = '';
        chatInput.style.height = 'auto';

        // Create message container for AI response
        const aiMessage = addMessage('', false);
        const streamSpan = aiMessage.querySelector('.stream-text');

        try {
            console.log('Fetching response from server...');
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Server error: ${response.status} - ${errorText}`);
            }

            console.log('Starting to read response stream...');
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { value, done } = await reader.read();
                if (done) {
                    console.log('Stream complete');
                    break;
                }
                
                const text = decoder.decode(value);
                console.log('Received chunk:', text);
                streamSpan.textContent += text;
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        } catch (error) {
            console.error('Error:', error);
            streamSpan.textContent = 'Error: ' + error.message;
            streamSpan.style.color = '#ff0000';
        }
    }
});
