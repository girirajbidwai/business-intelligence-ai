# Firmable AI Agent

Firmable is a powerful Business Intelligence AI Agent designed to autonomously analyze websites, extract structured business insights, and facilitate context-aware conversations using advanced RAG (Retrieval-Augmented Generation) techniques.

Built with a modern tech stack featuring **FastAPI**, **Groq**, **Pinecone Serverless Inference**, and **LangGraph**, Firmable offers a scalable and efficient solution for automated market research and competitive analysis.

## 🚀 Key Features

### 1. Autonomous Website Analysis
-   **Deep Crawling**: Automatically traverses websites (BFS depth 3) to gather comprehensive content beyond just the homepage.
-   **Structured Extraction**: Converts unstructured web content into strict JSON formats containing:
    -   Company Industry & Size
    -   Core Products & Unique Selling Propositions (USP)
    -   Contact Information (Emails, Phones, Social Media)
    -   Sentiment Analysis

### 2. Dynamic RAG System
-   **Per-URL Indexing**: Instantly creates a **dedicated, isolated Pinecone index** for every analyzed website.
-   **Serverless Inference**: Utilizes Pinecone's `llama-text-embed-v2` model directly on the server side for efficient embedding generation.
-   **Contextual Search**:Retrieves precise chunks of information to ground AI responses in factual website data.

### 3. Context-Aware Chat
-   **LangGraph Orchestration**: Manages conversation state and history using persistent SQLite checkpoints.
-   **Grounded Responses**: System prompts are dynamically injected with retrieved context to prevent hallucinations.
-   **Source Attribution**: Chat responses cite specific source URLs from the analyzed content.

---

## 🛠 Tech Stack

-   **Backend Framework**: FastAPI (Python)
-   **LLM Provider**: Groq (Llama 3 / Mixtral via API)
-   **Vector Database**: Pinecone (Serverless Inference)
-   **Agent Orchestration**: LangGraph
-   **Database**: SQLite (for chat session persistence)
-   **Scraping**: BeautifulSoup4 + AsyncIO

---

## 📋 Prerequisites

Before running the application, ensure you have the following:

1.  **Python 3.10+** installed.
2.  **Groq API Key**: Get one from [Groq Cloud](https://console.groq.com/).
3.  **Pinecone API Key**: Get one from [Pinecone Console](https://app.pinecone.io/). Ensure your project supports Serverless indexes.

---

## ⚙️ Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/your-username/firmable-ai.git
    cd firmable-ai
    ```

2.  **Create Virtual Environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**
    Create a `.env` file in the root directory:
    ```env
    # Core Security
    SECRET_KEY=your_super_secret_key_here

    # AI Providers
    GROQ_API_KEY=gsk_...
    PINECONE_API_KEY=pcsk_...

    # Configuration
    GROQ_MODEL=openai/gpt-oss-120b # or llama3-70b-8192
    ```

---

## 🏃‍♂️ Usage

### Start the Application
Run the development server using Uvicorn:
```bash
uvicorn app.main:app --reload
```
The server will start at `http://127.0.0.1:8000`.

### API Endpoints

#### 1. Analyze a Website (`POST /analyze`)
Triggers the scraping and deep analysis process.

**Request:**
```json
{
  "url": "https://example.com",
  "questions": ["What is their pricing model?"]
}
```

**Response:**
Returns structured JSON with company info, contact details, and specific answers to your questions.

#### 2. Chat with Data (`POST /chat`)
Engage in a multi-turn conversation about the analyzed specific website.

**Request:**
```json
{
  "url": "https://example.com",
  "query": "Who are their main competitors?",
  "thread_id": "session-123",
  "conversation_history": []
}
```

**Response:**
Returns the agent's answer derived strictly from the website's content, along with source references.

---

## 📂 Project Structure

```
firmable/
├── app/
│   ├── ai.py             # LangGraph workflow & LLM logic
│   ├── main.py           # FastAPI endpoints & entry point
│   ├── models.py         # Pydantic data models
│   ├── scraper.py        # Web scraping logic
│   ├── vector_store.py   # Pinecone dynamic indexing manager
│   ├── logging_config.py # Logger setup
│   └── templates/        # HTML templates for UI
├── tests/                # Unit & Integration tests
├── .env                  # Environment secrets
├── requirements.txt      # Python dependencies
└── README.md             # Documentation
```

## 🛡 License

This project is licensed under the MIT License.
