# Firmable AI Agent

Firmable AI is a high-performance FastAPI application designed to extract, synthesize, and interpret business insights from website homepages. It leverages Google Gemini AI and advanced web scraping to provide structured information and conversational follow-ups.

## 🚀 Features
- **Semantic Extraction**: Automatically identifies Industry, Company Size, USP, Target Audience, and Overall Sentiment.
- **Conversational AI**: A dedicated endpoint for asking follow-up questions with source citation.
- **Asynchronous Scraping**: Efficiently fetches and cleans website data.
- **Security**: Bearer token authentication for all API endpoints.
- **Rate Limiting**: Built-in protection against abuse.
- **Premium UI**: A sleek, modern dashboard for easy interaction.

## 🛠️ Architecture
```mermaid
graph TD
    User-->|REST API| FastAPI
    FastAPI-->|Scraper| Website
    FastAPI-->|AI Service| Gemini_LLM
    Gemini_LLM-->|Process| FastAPI
    FastAPI-->|Response| User
```

## 🧰 Tech Stack
- **FastAPI**: Main framework for high-performance API development.
- **Google Gemini (AI)**: Used for semantic extraction and conversational QA.
- **HTTPX & BeautifulSoup**: Asynchronous web scraping and cleaning.
- **Pydantic**: Robust data validation and serialization.
- **SlowAPI**: Rate limiting for security.
- **Vanilla CSS & JS**: Modern, responsive UI with glassmorphism.

## ⚙️ Setup & Installation

### 1. Prerequisites
- Python 3.9+
- A Google AI Studio API Key (for Gemini)

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
GEMINI_API_KEY=your_gemini_api_key_from_google_studio
```

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
    "url": "https://stripe.com",
    "questions": ["What is their main payment product?"]
}
```
**Auth**: `Authorization: Bearer your_custom_secret_token`

### Endpoint 2: Chat
**POST** `/chat`
```json
{
    "url": "https://stripe.com",
    "query": "How do they handle global payments?",
    "conversation_history": []
}
```

## 📝 IDE
Developed using VS Code / Cursor.
