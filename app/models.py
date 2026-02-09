from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict
from datetime import datetime

class ContactInfo(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    social_media: Dict[str, str] = Field(default_factory=dict)

class CompanyInfo(BaseModel):
    industry: str
    company_size: str
    location: str
    core_products_services: List[str]
    unique_selling_proposition: str
    target_audience: str
    contact_info: ContactInfo
    overall_sentiment: Optional[str] = None

class ExtractedAnswer(BaseModel):
    question: str
    answer: str

class AnalysisRequest(BaseModel):
    url: HttpUrl
    questions: Optional[List[str]] = None

class AnalysisResponse(BaseModel):
    url: HttpUrl
    analysis_timestamp: datetime
    company_info: CompanyInfo
    extracted_answers: List[ExtractedAnswer]

class ChatMessage(BaseModel):
    role: str # 'user' or 'assistant'
    content: str

class ChatRequest(BaseModel):
    url: HttpUrl
    query: str
    conversation_history: Optional[List[ChatMessage]] = None

class ChatResponse(BaseModel):
    url: HttpUrl
    user_query: str
    agent_response: str
    context_sources: List[str]
