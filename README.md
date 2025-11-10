# 🏥 Medical AI Assistant

An intelligent medical information assistant powered by AI that helps users get information about symptoms, conditions, and treatments. Built with Flask, CrewAI, and Google Gemini.

## ⚠️ Disclaimer

This AI assistant provides information for educational purposes only and is NOT a substitute for professional medical advice, diagnosis, or treatment. Always consult with a qualified healthcare provider for medical concerns.

## ✨ Features

- 💬 Interactive chat interface
- 🔍 Web search integration for up-to-date medical information
- 📚 RAG (Retrieval Augmented Generation) support for custom medical documents
- 🤖 Powered by Google Gemini AI
- 🎨 Modern, responsive UI

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- Google Gemini API key
- Serper API key (for web search)

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd Medicine-Suggestion-AI
```

2. Create a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Mac/Linux
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Add your API keys:
     - Get Gemini API key from: https://makersuite.google.com/app/apikey
     - Get Serper API key from: https://serper.dev

5. (Optional) Add medical PDF documents to the `data/` folder for RAG functionality

### Running the Application

```bash
python app.py
```

Open your browser and navigate to: `http://127.0.0.1:5000`

## 📁 Project Structure

```
Medicine-Suggestion-AI/
├── app.py              # Flask backend with CrewAI agents
├── index.html          # Frontend chat interface
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (not in git)
├── .env.example       # Example environment variables
├── data/              # Optional: PDF documents for RAG
└── README.md          # This file
```

## 🛠️ Technologies Used

- **Backend**: Flask, CrewAI, LangChain
- **AI Model**: Google Gemini
- **Search**: SerperDev API
- **Vector Store**: FAISS
- **Embeddings**: HuggingFace (all-MiniLM-L6-v2)
- **Frontend**: HTML, CSS, JavaScript

## 📝 Usage

1. Type your medical question in the chat interface
2. The AI will search through uploaded documents first (if available)
3. If needed, it will search the web for additional information
4. Receive a comprehensive, evidence-based response

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is open source and available under the MIT License.

## 🔗 Links

- [Google Gemini](https://ai.google.dev/)
- [CrewAI](https://www.crewai.com/)
- [Serper API](https://serper.dev/)
