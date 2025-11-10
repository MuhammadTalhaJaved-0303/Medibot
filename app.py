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

# Set up the language model - use litellm format directly
from litellm import completion
llm = "gemini/gemini-1.5-flash"

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
    role='Medical Research Specialist',
    goal='To provide accurate, evidence-based medical information by searching through provided documents and the web.',
    backstory=(
        "You are an expert medical researcher with a background in clinical studies and pharmacology. "
        "You are skilled at dissecting complex medical topics and presenting them in a clear, understandable way. "
        "Your primary function is to consult a vector database of medical documents to answer user queries. "
        "If the information is not found in the documents, you then use your web search capabilities to find a reliable answer."
    ),
    verbose=True,
    allow_delegation=False,
    tools=agent_tools,
    llm=llm
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
        Answer the user's medical question based on the provided documents and your general knowledge.
        The user's question is: "{user_input}"

        **IMPORTANT INSTRUCTIONS:**
        1.  **PRIORITIZE DOCUMENTS:** If a 'medical_document_search' tool is available, use it FIRST to search the provided medical documents for an answer.
        2.  **WEB SEARCH AS BACKUP:** If the documents do not contain a relevant answer, use the web search tool to find information from reputable medical sources (e.g., Mayo Clinic, WebMD, WHO).
        3.  **DISCLAIMER:** ALWAYS start your final answer with the following disclaimer:
            '***Disclaimer: I am an AI assistant and not a medical professional. The information I provide is for informational purposes only and not a substitute for professional medical advice, diagnosis, or treatment. Always consult with a qualified healthcare provider for any medical concerns.***'
        4.  **SAFETY FIRST:** Do NOT provide a diagnosis. You can give information about conditions, but you must state that a doctor is required for a real diagnosis. If the query seems urgent or life-threatening (e.g., chest pain, difficulty breathing), your primary response should be to advise seeking immediate medical attention.
        """,
        agent=medical_research_agent,
        expected_output="A clear, concise, and helpful answer to the user's question, formatted in markdown, starting with the mandatory disclaimer."
    )

    # Create and run the crew
    medical_crew = Crew(
        agents=[medical_research_agent],
        tasks=[research_task],
        process=Process.sequential,
        verbose=True
    )

    try:
        result = medical_crew.kickoff()
        return jsonify({'response': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
