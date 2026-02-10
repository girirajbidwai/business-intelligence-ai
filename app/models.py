from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict
from datetime import datetime

class ContactInfo(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    social_media: Dict[str, Optional[str]] = Field(default_factory=dict)

class CompanyInfo(BaseModel):
    industry: Optional[str] = "Information not found"
    company_size: Optional[str] = "Information not found"
    location: Optional[str] = "Information not found"
    core_products_services: List[str] = Field(default_factory=list)
    unique_selling_proposition: Optional[str] = "Information not found"
    target_audience: Optional[str] = "Information not found"
    contact_info: ContactInfo = Field(default_factory=ContactInfo)
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
    thread_id: Optional[str] = "default_thread"
    conversation_history: Optional[List[ChatMessage]] = None

class ChatResponse(BaseModel):
    url: HttpUrl
    user_query: str
    agent_response: str
    context_sources: List[str]
