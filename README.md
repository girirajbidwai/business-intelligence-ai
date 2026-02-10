# Firmable AI Agent

Firmable AI is a high-performance FastAPI application designed to extract, synthesize, and interpret business insights from website homepages. It leverages **Groq (Llama 3)** and advanced web scraping to provide structured information and conversational follow-ups.

## 🚀 Features
- **Semantic Extraction**: Automatically identifies Industry, Company Size, USP, Target Audience, and Overall Sentiment.
- **Conversational AI**: A dedicated chat endpoint with persistent memory (LangGraph + SQLite) for contextual follow-up questions.
- **Asynchronous Scraping**: Efficiently fetches and cleans website data.
- **Security**: Bearer token authentication for all API endpoints.
- **Rate Limiting**: Built-in protection against abuse.
- **Premium UI**: A sleek, modern dashboard for easy interaction.

## 🛠️ Architecture
```mermaid
graph TD
    User-->|REST API| FastAPI
    FastAPI-->|Scraper| Website
    FastAPI-->|AI Service| Groq_LLM
    Groq_LLM-->|Process| FastAPI
    FastAPI-->|Response| User
```

## 🧰 Tech Stack
- **FastAPI**: Main framework for high-performance API development.
- **Groq (Llama 3)**: Ultra-fast inference for semantic extraction and conversational QA.
- **LangGraph + SQLite**: Persistent conversational memory with thread-based state management.
- **HTTPX & BeautifulSoup**: Asynchronous web scraping and cleaning.
- **Pydantic**: Robust data validation and serialization.
- **SlowAPI**: Rate limiting for security.
- **Vanilla CSS & JS**: Modern, responsive UI with glassmorphism.

## ⚙️ Setup & Installation

### 1. Prerequisites
- Python 3.9+
- A Groq API Key (from [console.groq.com](https://console.groq.com))

### 2. Installation
```powershell
# Clone the repository (if applicable)
# Navigate to project directory
cd Firmable

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory:
```env
SECRET_KEY=your_custom_secret_token
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama3-70b-8192
```
> **Note**: `GROQ_MODEL` is optional and defaults to `llama3-70b-8192`. See [Groq supported models](https://console.groq.com/docs/models) for alternatives.

### 4. Running the Application
```powershell
uvicorn app.main:app --reload
```
Open `http://localhost:8000` in your browser to access the UI.

## 📡 API Usage Examples

### Endpoint 1: Analyze Website
**POST** `/analyze`
```json
{
    "url": "https://firmable.com/",
    "questions": ["What is their main payment product?"]
}
```
**Auth**: `Authorization: Bearer your_custom_secret_token`

### Endpoint 2: Chat
**POST** `/chat`
```json
{
    "url": "https://firmable.com/",
    "query": "How do they handle global payments?",
    "thread_id": "optional_thread_id",
    "conversation_history": []
}
```

## 📝 IDE
Developed using VS Code / Cursor.
