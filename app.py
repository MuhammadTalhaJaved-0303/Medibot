import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.tools import create_retriever_tool
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Check for GEMINI_API_KEY
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")

# Set up environment variable for Google API key (required by litellm)
os.environ["GOOGLE_API_KEY"] = gemini_api_key

# Set up the language model - use litellm format directly with optimized settings
llm = "gemini/gemini-2.5-flash"  # Flash model is already the fastest

# --- Document Loading and RAG Setup (Re-enabled) ---
agent_tools = []
data_dir = "data/"
documents = []
if os.path.exists(data_dir):
    for filename in os.listdir(data_dir):
        if filename.endswith(".pdf"):
            loader = PyPDFLoader(os.path.join(data_dir, filename))
            documents.extend(loader.load())

if documents:
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    splits = text_splitter.split_documents(documents)
    vectorstore = FAISS.from_documents(documents=splits, embedding=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"))
    retriever = vectorstore.as_retriever()
    
    retriever_tool = create_retriever_tool(
        retriever,
        "medical_document_search",
        "Search for information in the provided medical documents. Use this tool FIRST to find specific information about symptoms, conditions, and treatments mentioned in the uploaded PDFs."
    )
    agent_tools.append(retriever_tool)

# --- Tool Definition ---
# Use the official tool from the crewai-tools package
search_tool = SerperDevTool()
agent_tools.append(search_tool)

# --- CrewAI Agent Definition ---
medical_research_agent = Agent(
    role='Expert Medical Information Specialist',
    goal='Provide comprehensive, accurate medical information including detailed medicine recommendations with brand names, dosages, and practical guidance.',
    backstory=(
        "You are an experienced medical information specialist with extensive knowledge of "
        "medications, treatments, and medical conditions. You provide detailed, practical advice "
        "including specific medicine names (both generic and brand names), dosage information, "
        "timing, warnings, and local availability. You explain medical concepts clearly and "
        "help people understand their treatment options while emphasizing the importance of "
        "professional medical consultation."
    ),
    verbose=False,  # Disable verbose logging for speed
    allow_delegation=False,
    tools=agent_tools,
    llm=llm,
    max_iter=5  # Increased for more thorough research
)

import json
import uuid
from datetime import datetime

# --- Chat History Management ---
CHATS_FILE = "chats.json"

def load_chats():
    if not os.path.exists(CHATS_FILE):
        return {}
    try:
        with open(CHATS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_chats(chats):
    with open(CHATS_FILE, 'w') as f:
        json.dump(chats, f, indent=2)

def get_chat_history():
    chats = load_chats()
    # Return list of summaries sorted by timestamp (newest first)
    history = []
    for session_id, data in chats.items():
        history.append({
            'id': session_id,
            'title': data.get('title', 'New Chat'),
            'timestamp': data.get('timestamp', ''),
            'preview': data['messages'][-1]['content'][:50] + "..." if data['messages'] else "Empty chat"
        })
    return sorted(history, key=lambda x: x['timestamp'], reverse=True)

def get_chat_session(session_id):
    chats = load_chats()
    return chats.get(session_id, {'messages': []})

def save_message(session_id, role, content):
    chats = load_chats()
    if session_id not in chats:
        chats[session_id] = {
            'title': 'New Chat',
            'timestamp': datetime.now().isoformat(),
            'messages': []
        }
    
    chats[session_id]['messages'].append({
        'role': role,
        'content': content,
        'timestamp': datetime.now().isoformat()
    })
    
    # Update title if it's the first user message
    if role == 'user' and len(chats[session_id]['messages']) <= 2: # <= 2 because system/welcome might be there? No, we just add user/bot.
        # Simple title generation: first few words
        chats[session_id]['title'] = content[:30] + "..." if len(content) > 30 else content
        
    chats[session_id]['timestamp'] = datetime.now().isoformat()
    save_chats(chats)

import google.generativeai as genai
from PIL import Image
import io

# Configure GenAI
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)

def analyze_image(image_file):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        img = Image.open(image_file)
        response = model.generate_content([
            "Analyze this medical image (lab report, prescription, medicine packaging, or symptom) in detail. "
            "If it's text, extract it accurately. If it's a symptom, describe it. "
            "If it's a medicine, identify the name and dosage.", 
            img
        ])
        return response.text
    except Exception as e:
        return f"Error analyzing image: {str(e)}"

# --- Routes ---
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

@app.route('/history', methods=['GET'])
def get_history():
    return jsonify(get_chat_history())

@app.route('/history/<session_id>', methods=['GET'])
def get_session(session_id):
    session = get_chat_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    return jsonify(session)

@app.route('/history/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    chats = load_chats()
    if session_id in chats:
        del chats[session_id]
        save_chats(chats)
        return jsonify({'success': True})
    return jsonify({'error': 'Session not found'}), 404

@app.route('/chat', methods=['POST'])
def chat():
    # Handle both JSON and Multipart requests
    if request.is_json:
        data = request.json
        user_input = data.get('message')
        session_id = data.get('session_id')
        image_file = None
    else:
        user_input = request.form.get('message')
        session_id = request.form.get('session_id')
        image_file = request.files.get('image')
    
    if not user_input and not image_file:
        return jsonify({'error': 'No message or image provided'}), 400

    # Generate new session ID if not provided
    if not session_id or session_id == 'null':
        session_id = str(uuid.uuid4())

    # Process Image if present
    image_context = ""
    if image_file:
        image_analysis = analyze_image(image_file)
        image_context = f"\n\n[IMAGE ANALYSIS DATA]:\nThe user uploaded an image. Here is the analysis of that image:\n{image_analysis}\n"
        # Append to user input for storage/display
        if not user_input:
            user_input = "Analyze this image."
        
        # Save a note about the image in history (we don't save the actual image bytes to JSON)
        save_message(session_id, 'user', f"{user_input} [Attached Image]")
    else:
        save_message(session_id, 'user', user_input)

    # Create the task for the agent
    research_task = Task(
        description=f"""
        User question: "{user_input}"
        {image_context}

        Provide a comprehensive, helpful medical response following these guidelines:

        1. **For Medicine Recommendations:**
           - Categorize medicines by type (Antiviral/Prescription, OTC symptom relief, etc.)
           - Include specific brand names and generic names (e.g., "Paracetamol (Panadol, Tylenol)")
           - Explain what each medicine does and when to use it
           - Include dosage guidance if relevant
           - Mention timing (e.g., "most effective within 48 hours of symptoms")
           - Add important warnings (e.g., don't give aspirin to children, check for drug interactions)
           - Provide local context (medicines available in Pakistan/user's region if known)
           - End with: "⚠️ It's strongly recommended to consult a doctor before taking any medication to ensure it's safe and appropriate for your specific situation."

        2. **For Symptom/Condition Questions:**
           - Explain the condition clearly
           - List common symptoms
           - Suggest treatment options (home remedies, OTC medicines, when to see a doctor)
           - Include prevention tips if relevant

        3. **For Emergencies:**
           - Immediately advise seeking medical attention
           - List warning signs to watch for

        4. **General Guidelines:**
           - Be detailed and informative like a knowledgeable medical assistant
           - Use bullet points and clear formatting
           - Cite reliable sources when possible (WHO, CDC, medical journals)
           - Be empathetic and helpful
           - Search documents first, then use web search for comprehensive information
        """,
        agent=medical_research_agent,
        expected_output="A detailed, well-structured medical response with specific medicine names, dosages, warnings, and practical advice."
    )

    # Create and run the crew
    medical_crew = Crew(
        agents=[medical_research_agent],
        tasks=[research_task],
        process=Process.sequential,
        verbose=False,  # Disable verbose for speed
        memory=False,  # Disable memory for faster responses
        cache=True  # Enable caching for repeated queries
    )

    try:
        result = medical_crew.kickoff()
        # Extract the actual text from CrewOutput
        response_text = str(result.raw) if hasattr(result, 'raw') else str(result)
        
        # Save bot response
        save_message(session_id, 'bot', response_text)
        
        return jsonify({
            'response': response_text,
            'session_id': session_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
