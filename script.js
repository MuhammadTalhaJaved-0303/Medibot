document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chatContainer');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    const historyList = document.getElementById('historyList');
    const newChatBtn = document.getElementById('newChatBtn');

    // Image Upload Elements
    const imageInput = document.getElementById('imageInput');
    const attachBtn = document.getElementById('attachBtn');

    async function loadHistory() {
        try {
            const response = await fetch('/history');
            const history = await response.json();
            renderHistory(history);
        } catch (error) {
            console.error('Error loading history:', error);
        }
    }

    function renderHistory(history) {
        historyList.innerHTML = '';
        history.forEach(item => {
            const div = document.createElement('div');
            div.className = `history-item ${item.id === currentSessionId ? 'active' : ''}`;
            div.innerHTML = `
                <span>${item.title}</span>
                <button class="delete-btn" title="Delete chat">×</button>
            `;

            // Handle click on the item (load session)
            div.onclick = (e) => {
                // If clicked on delete button, don't load session
                if (e.target.classList.contains('delete-btn')) {
                    deleteSession(e, item.id);
                } else {
                    loadSession(item.id);
                }
            };

            historyList.appendChild(div);
        });
    }

    async function loadSession(sessionId) {
        try {
            const response = await fetch(`/history/${sessionId}`);
            const data = await response.json();

            currentSessionId = sessionId;
            chatContainer.innerHTML = ''; // Clear current chat
            clearImageSelection(); // Clear any pending image

            // Re-render history to update active state
            loadHistory();

            // Render messages
            data.messages.forEach(msg => {
                addMessage(msg.content, msg.role === 'user');
            });
        } catch (error) {
            console.error('Error loading session:', error);
        }
    }

    async function deleteSession(event, sessionId) {
        event.stopPropagation(); // Prevent triggering loadSession
        if (!confirm('Are you sure you want to delete this chat?')) return;

        try {
            await fetch(`/history/${sessionId}`, { method: 'DELETE' });
            if (currentSessionId === sessionId) {
                startNewChat();
            } else {
                loadHistory();
            }
        } catch (error) {
            console.error('Error deleting session:', error);
        }
    }

    function startNewChat() {
        currentSessionId = null;
        clearImageSelection();
        chatContainer.innerHTML = `
            <div class="message bot">
                <div class="avatar">🤖</div>
                <div class="message-content">
                    Hello! I'm MediBot, your AI Medical Assistant. I can help answer questions about medical conditions, symptoms, and treatments. Please note that I'm not a substitute for professional medical advice. How can I help you today?
                </div>
            </div>
        `;
        loadHistory();
    }

    function addMessage(content, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user' : 'bot'}`;

        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.textContent = isUser ? '👤' : '🤖';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        // Format content if it's from bot
        if (!isUser) {
            content = content
                .replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>')
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/\n/g, '<br>');
        }

        contentDiv.innerHTML = content;

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function showLoading() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message bot';
        loadingDiv.id = 'loading';
        loadingDiv.innerHTML = `
            <div class="avatar">🤖</div>
            <div class="message-content">
                <div class="loading">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        chatContainer.appendChild(loadingDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function removeLoading() {
        const loading = document.getElementById('loading');
        if (loading) {
            loading.remove();
        }
    }

    async function sendMessage() {
        const message = userInput.value.trim();
        const imageFile = imageInput ? imageInput.files[0] : null;

        if (!message && !imageFile) return;

        // Add user message
        let displayMessage = message;
        if (imageFile) {
            displayMessage = message ? `${message} <br><em>[Attached Image: ${imageFile.name}]</em>` : `<em>[Attached Image: ${imageFile.name}]</em>`;
        }

        addMessage(displayMessage, true);
        userInput.value = '';

        // Prepare request data
        let body;
        let headers = {};

        if (imageFile) {
            const formData = new FormData();
            formData.append('message', message);
            if (currentSessionId) formData.append('session_id', currentSessionId);
            formData.append('image', imageFile);
            body = formData;
            // Content-Type header is automatically set by browser for FormData
        } else {
            body = JSON.stringify({
                message: message,
                session_id: currentSessionId
            });
            headers['Content-Type'] = 'application/json';
        }

        // Clear image selection immediately after sending
        clearImageSelection();

        sendBtn.disabled = true;

        // Show loading
        showLoading();

        try {
            const response = await fetch('http://127.0.0.1:5000/chat', {
                method: 'POST',
                headers: headers,
                body: body
            });

            removeLoading();

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();

            // Update current session ID if it was a new chat
            if (data.session_id) {
                currentSessionId = data.session_id;
                loadHistory(); // Refresh sidebar to show new chat title
            }

            // Format the response
            let botResponse = data.response;
            if (typeof botResponse === 'object') {
                botResponse = botResponse.raw || JSON.stringify(botResponse);
            }

            addMessage(botResponse);
        } catch (error) {
            removeLoading();
            addMessage('Sorry, there was an error processing your request. Please try again.', false);
            console.error('Error:', error);
        } finally {
            sendBtn.disabled = false;
            userInput.focus();
        }
    }
});
