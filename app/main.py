import os
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

from .models import (
    AnalysisRequest, AnalysisResponse, 
    ChatRequest, ChatResponse,
    CompanyInfo, ContactInfo, ExtractedAnswer
)
from .scraper import scrape_homepage
from .ai import AIService

load_dotenv()

# Initialize Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Firmable AI Agent")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security
security = HTTPBearer()
API_SECRET_KEY = os.getenv("SECRET_KEY", "default_secret")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not found in environment variables.")

ai_service = AIService(api_key=GEMINI_API_KEY)
print("Firmable AI Agent: AI Service initialized.")

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return credentials.credentials

# Templates for UI
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/analyze", response_model=AnalysisResponse)
@limiter.limit("5/minute")
async def analyze_website(
    request: Request,
    payload: AnalysisRequest,
    token: str = Depends(verify_token)
):
    try:
        # Re-initialize or check key if needed, or just let it fail and catch it
        content = await scrape_homepage(str(payload.url))
        analysis = await ai_service.analyze_content(content, payload.questions)
        
        # Structure the response
        response = AnalysisResponse(
            url=payload.url,
            analysis_timestamp=datetime.utcnow(),
            company_info=CompanyInfo(**analysis.get("company_info", {})),
            extracted_answers=[ExtractedAnswer(**ans) for ans in analysis.get("extracted_answers", [])]
        )
        return response
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat_with_website(
    request: Request,
    payload: ChatRequest,
    token: str = Depends(verify_token)
):
    try:
        content = await scrape_homepage(str(payload.url))
        chat_result = await ai_service.chat_interaction(
            content=content,
            query=payload.query,
            thread_id=payload.thread_id,
            history=payload.conversation_history
        )
        
        return ChatResponse(
            url=payload.url,
            user_query=payload.query,
            agent_response=chat_result.get("agent_response", "I generated a response but failed to parse it."),
            context_sources=chat_result.get("context_sources", ["Homepage content analysis"])
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
