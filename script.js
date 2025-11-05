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
    // Use the environment's API key (empty string)
    const GEMINI_API_KEY = ""; 
    // Use the model compatible with the environment's key
    const API_URL = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key=`;

    // System instruction for the medical chatbot
    const SYSTEM_INSTRUCTION = {
        role: "system",
        parts: [{
            text: "You are 'MediBot', an AI medical assistant. Your purpose is to provide helpful, safe, and informational responses to general health-related queries. \n\n**Core Directives:**\n1.  **Strict Disclaimer:** You MUST begin your very first response in any new chat session with this exact disclaimer: '***Disclaimer: I am an AI assistant and not a medical professional. The information I provide is for informational purposes only and not a substitute for professional medical advice, diagnosis, or treatment. Always consult with a qualified healthcare provider for any medical concerns.***' \n2.  **Safety First:** You must NOT provide diagnoses, prescribe treatments, or interpret specific medical results. \n3.  **General Information:** You CAN provide general information about medical conditions, symptoms, wellness, nutrition, and prevention. \n4.  **Symptom Analysis (General):** If a user describes symptoms, you can list *potential* associated conditions in a general way, but you MUST immediately follow up by strongly advising them to consult a healthcare professional for a proper diagnosis.\n5.  **Triage for Urgency:** If symptoms sound potentially life-threatening (e.g., 'chest pain', 'difficulty breathing', 'severe bleeding', 'suicidal thoughts'), your ONLY response should be to advise seeking immediate emergency medical help (e.g., 'Call 911' or your local emergency number) or a crisis hotline. Do not attempt to analyze these symptoms further.\n6.  **Empathetic Tone:** Maintain a calm, empathetic, and professional tone.\n7.  **Scope Limitation:** If asked questions outside the medical/health domain, politely state that your function is limited to health-related topics."
        }]
    };

    // Function to check and get API Key
    function initializeApp() {
        // No API key to check, just initialize the chat
        initChat();
    }

    // Removed saveApiKey function

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
        if (chatHistory.length > 0) return; // Don't re-initialize
        
        // Add a temporary "system" message to start the conversation
        // This will be replaced by the AI's first response
        chatHistory.push({ role: "system", parts: [{ text: "Start conversation" }] });
        
        loadingIndicator.classList.remove('hidden');
        chatContainer.scrollTop = chatContainer.scrollHeight;

        try {
            // Call the AI with just the system prompt to get the initial disclaimer
            const aiResponse = await callMedicalAI(chatHistory);
            
            // The first message *is* the disclaimer
            addMessage('bot', aiResponse); 
            
            // Reset chat history to only include the system instruction and the bot's first message
            chatHistory = [
                SYSTEM_INSTRUCTION,
                { role: 'model', parts: [{ text: aiResponse }] }
            ];

        } catch (error) {
            console.error("Error calling Gemini API:", error);
            // Updated error message
            showError(`Failed to initialize chat. ${error.message}. Please reload the page and try again.`);
            // Clear the bad history
            chatHistory = [];
        } finally {
            loadingIndicator.classList.add('hidden');
        }
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
        // Removed API key check
        if (prompt === '') {
            return;
        }

        // Add user message to UI
        addMessage('user', prompt);
        userInput.value = '';
        loadingIndicator.classList.remove('hidden');
        chatContainer.scrollTop = chatContainer.scrollHeight;

        // Add user message to history
        chatHistory.push({ role: 'user', parts: [{ text: prompt }] });

        try {
            // Call the Gemini API
            const aiResponse = await callMedicalAI(chatHistory);

            // Add AI response to UI
            addMessage('bot', aiResponse);

            // Add AI response to history
            chatHistory.push({ role: 'model', parts: [{ text: aiResponse }] });

        } catch (error) {
            console.error("Error calling Gemini API:", error);
            // Updated error message
            showError(`Error: ${error.message}. The AI could not be reached. Please check your network connection and try again.`);
            // Remove the user's message from history if the call failed
            chatHistory.pop();
        } finally {
            loadingIndicator.classList.add('hidden');
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }

    // Function to call the Gemini API
    async function callMedicalAI(history) {
        // Removed API key check, as it's now a const
        
        const fullApiUrl = API_URL + GEMINI_API_KEY;

        // Construct the payload
        const payload = {
            // We send all history except the very first system prompt
            // The systemInstruction block is used instead
            contents: history.filter(msg => msg.role !== 'system'),
            systemInstruction: SYSTEM_INSTRUCTION,
            safetySettings: [
                { category: "HARM_CATEGORY_HARASSMENT", threshold: "BLOCK_MEDIUM_AND_ABOVE" },
                { category: "HARM_CATEGORY_HATE_SPEECH", threshold: "BLOCK_MEDIUM_AND_ABOVE" },
                { category: "HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold: "BLOCK_MEDIUM_AND_ABOVE" },
                { category: "HARM_CATEGORY_DANGEROUS_CONTENT", threshold: "BLOCK_MEDIUM_AND_ABOVE" }
            ],
            generationConfig: {
                temperature: 0.7,
                topK: 1,
                topP: 1,
                maxOutputTokens: 2048,
            }
        };

        // Add exponential backoff
        let response;
        let delay = 1000; // start with 1 second
        for (let i = 0; i < 3; i++) { // Retry up to 3 times
            try {
                response = await fetch(fullApiUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });

                if (response.status === 429) { // Throttling
                    throw new Error("Throttled");
                }
                
                if (!response.ok) {
                    let errorBody = "Unknown error";
                    try {
                        errorBody = await response.json();
                        errorBody = errorBody?.error?.message || JSON.stringify(errorBody);
                    } catch(e) { /* ignore parsing error */ }
                    
                    console.error("API Error Response:", response.status, errorBody);
                    // Updated error to be more specific
                    throw new Error(`API Error: ${errorBody} (Status: ${response.status})`);
                }

                // Success, break retry loop
                break; 
            
            } catch (error) {
                if (error.message === "Throttled") {
                    console.warn(`API call throttled. Retrying in ${delay}ms...`);
                    await new Promise(res => setTimeout(res, delay));
                    delay *= 2; // Double the delay
                } else {
                    throw error; // Re-throw other errors
                }
            }
        }
        
        if (!response.ok) {
             // Updated error to be more specific
             throw new Error(`API Error: Something went wrong (Status: ${response.status})`);
        }

        const result = await response.json();

        if (result.candidates && result.candidates.length > 0 &&
            result.candidates[0].content && result.candidates[0].content.parts &&
            result.candidates[0].content.parts.length > 0) {
            
            return result.candidates[0].content.parts[0].text;
        } else if (result.promptFeedback) {
            // Handle blocked prompt
            const blockReason = result.promptFeedback.blockReason || "Unknown safety block";
            const safetyRatings = result.promptFeedback.safetyRatings.map(r => `${r.category}: ${r.probability}`).join(', ');
            console.warn(`Prompt blocked. Reason: ${blockReason}. Ratings: [${safetyRatings}]`);
            return `I'm sorry, I can't respond to that request. It may violate my safety guidelines. (Reason: ${blockReason})`;
        }
        
        throw new Error("No content received from API.");
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
    initializeApp();
});
