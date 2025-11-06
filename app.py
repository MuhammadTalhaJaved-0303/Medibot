import os
from flask import Flask, request, jsonify
from langchain_google_genai import ChatGoogleGenerativeAI
from crewai import Agent, Task, Crew, Process
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain.tools import Tool
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Check for GEMINI_API_KEY
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")

# Set up the language model
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-pro-latest", google_api_key=gemini_api_key)

# --- Tool Definition ---
# To resolve the persistent Pydantic validation errors, we will define the tool
# using a more robust and explicit method that is less prone to environment conflicts.
search_tool = Tool(
    name="DuckDuckGo Search",
    description="A wrapper around DuckDuckGo Search. Useful for when you need to answer questions about current events or find medical information from reputable sources. Input should be a search query.",
    func=DuckDuckGoSearchAPIWrapper().run,
)

# --- CrewAI Agent Definition ---
medical_research_agent = Agent(
    role='Medical Research Specialist',
    goal='To provide accurate, evidence-based medical information by searching the web.',
    backstory=(
        "You are an expert medical researcher with a background in clinical studies and pharmacology. "
        "You are skilled at dissecting complex medical topics and presenting them in a clear, understandable way. "
        "You use your web search capabilities to find reliable answers to user queries."
    ),
    verbose=True,
    allow_delegation=False,
    tools=[search_tool],
    llm=llm
)

# --- API Endpoint ---
@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message')
    if not user_input:
        return jsonify({'error': 'No message provided'}), 400

    # Create the task for the agent
    research_task = Task(
        description=f"""
        Answer the user's medical question based on your general knowledge and web search results.
        The user's question is: "{user_input}"

        **IMPORTANT INSTRUCTIONS:**
        1.  **WEB SEARCH:** Use the web search tool to find information from reputable medical sources (e.g., Mayo Clinic, WebMD, WHO).
        2.  **DISCLAIMER:** ALWAYS start your final answer with the following disclaimer:
            '***Disclaimer: I am an AI assistant and not a medical professional. The information I provide is for informational purposes only and not a substitute for professional medical advice, diagnosis, or treatment. Always consult with a qualified healthcare provider for any medical concerns.***'
        3.  **SAFETY FIRST:** Do NOT provide a diagnosis. You can give information about conditions, but you must state that a doctor is required for a real diagnosis. If the query seems urgent or life-threatening (e.g., chest pain, difficulty breathing), your primary response should be to advise seeking immediate medical attention.
        """,
        agent=medical_research_agent,
        expected_output="A clear, concise, and helpful answer to the user's question, formatted in markdown, starting with the mandatory disclaimer."
    )

    # Create and run the crew
    medical_crew = Crew(
        agents=[medical_research_agent],
        tasks=[research_task],
        process=Process.sequential,
        verbose=2
    )

    try:
        result = medical_crew.kickoff()
        return jsonify({'response': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
