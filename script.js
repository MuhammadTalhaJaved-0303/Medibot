document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chat-container');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const loadingIndicator = document.getElementById('loading-indicator');
    const clearChatBtn = document.getElementById('clear-chat-btn');
    
    // Removed API Key Elements
    
    // Error Modal Elements
    const errorModal = document.getElementById('error-modal');
    const errorMessage = document.getElementById('error-message');
    const errorOkBtn = document.getElementById('error-ok-btn');

    let chatHistory = [];
    // API details are now handled by the backend
    const API_URL = '/chat'; // The new backend endpoint

    // System instruction for the medical chatbot is now handled by the backend
    // const SYSTEM_INSTRUCTION = { ... };

    // Function to check and get API Key is no longer needed

    // Function to show error modal
    function showError(message) {
        errorMessage.textContent = message;
        errorModal.classList.remove('hidden');
    }

    // Function to hide error modal
    function hideError() {
        errorModal.classList.add('hidden');
    }

    // Function to initialize the chat with the disclaimer
    async function initChat() {
        // The backend will now provide the initial disclaimer
        addMessage('bot', '***Disclaimer: I am an AI assistant and not a medical professional. The information I provide is for informational purposes only and not a substitute for professional medical advice, diagnosis, or treatment. Always consult with a qualified healthcare provider for any medical concerns.***');
    }

    // Function to add a message to the chat UI
    function addMessage(sender, text) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', 'p-4', 'rounded-lg', 'max-w-xl');
        
        if (sender === 'user') {
            messageDiv.classList.add('bg-blue-500', 'text-white', 'self-end', 'ml-auto');
        } else {
            messageDiv.classList.add('bg-white', 'text-gray-800', 'self-start', 'mr-auto', 'shadow-sm');
        }

        // Sanitize text before treating as HTML (basic sanitization)
        let formattedText = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\n/g, '<br>')
            .replace(/\*\*\*(.*?)\*\*\*/g, '<br><strong><em>$1</em></strong><br>') // Bold Italic with breaks
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
            .replace(/\*(.*?)\*/g, '<em>$1</em>'); // Italic

        messageDiv.innerHTML = formattedText;
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Function to handle sending a message
    async function sendMessage() {
        const prompt = userInput.value.trim();
        if (prompt === '') {
            return;
        }

        // Add user message to UI
        addMessage('user', prompt);
        userInput.value = '';
        loadingIndicator.classList.remove('hidden');
        chatContainer.scrollTop = chatContainer.scrollHeight;

        try {
            // Call the new backend API
            const aiResponse = await callMedicalBackend(prompt);

            // Add AI response to UI
            addMessage('bot', aiResponse);

        } catch (error) {
            console.error("Error calling backend:", error);
            showError(`Error: ${error.message}. The AI backend could not be reached. Please check your connection and try again.`);
        } finally {
            loadingIndicator.classList.add('hidden');
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }

    // Function to call the backend API
    async function callMedicalBackend(message) {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Backend Error: Status ${response.status}`);
        }

        const result = await response.json();
        return result.response;
    }

    // Function to clear chat
    function clearChat() {
        chatContainer.innerHTML = '';
        chatHistory = [];
        // Re-initialize the chat to get the disclaimer
        initChat();
    }

    // Event Listeners
    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    clearChatBtn.addEventListener('click', clearChat);
    
    // Removed API Key Listeners

    // Error Modal Listener
    errorOkBtn.addEventListener('click', hideError);

    // Initialize the app
    initChat(); // Changed from initializeApp to initChat
});
