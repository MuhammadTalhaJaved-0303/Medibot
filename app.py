import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.tools.retriever import create_retriever_tool
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

# --- Routes ---
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message')
    if not user_input:
        return jsonify({'error': 'No message provided'}), 400

    # Create the task for the agent
    research_task = Task(
        description=f"""
        User question: "{user_input}"

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
        return jsonify({'response': response_text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
