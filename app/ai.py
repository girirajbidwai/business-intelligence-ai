import google.generativeai as genai
import json
import os
from typing import List, Optional
from .models import CompanyInfo, ExtractedAnswer, ChatMessage

class AIService:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Gemini API Key is missing. Please set GEMINI_API_KEY in your .env file.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})

    async def analyze_content(self, content: str, questions: Optional[List[str]] = None) -> dict:
        prompt = f"""
        Analyze the following website content and extract key business insights.
        
        Website Content:
        {content}
        
        Return a JSON object with this exact structure:
        {{
            "company_info": {{
                "industry": "Primary industry",
                "company_size": "Estimated size (small/medium/large or count)",
                "location": "Headquarters location",
                "core_products_services": ["list", "of", "products"],
                "unique_selling_proposition": "What makes them stand out",
                "target_audience": "Primary customer demographic",
                "overall_sentiment": "Positive/Neutral/Professional etc.",
                "contact_info": {{
                    "email": "email if found",
                    "phone": "phone if found",
                    "social_media": {{"linkedin": "url", "twitter": "url", "etc": "url"}}
                }}
            }},
            "extracted_answers": [
                {{"question": "question string", "answer": "answer string"}}
            ]
        }}
        
        Additional Questions to answer if they aren't covered:
        {questions if questions else "None"}
        """
        
        response = self.model.generate_content(prompt)
        try:
            return json.loads(response.text)
        except Exception as e:
            # Fallback for manual parsing if JSON mode isn't perfectly strict
            text = response.text.replace("```json", "").replace("```", "").strip()
            try:
                return json.loads(text)
            except:
                raise ValueError(f"Failed to parse AI response: {str(e)}")

    async def chat_interaction(self, content: str, query: str, history: Optional[List[ChatMessage]] = None) -> dict:
        history_prompts = ""
        if history:
            for msg in history:
                history_prompts += f"{msg.role.upper()}: {msg.content}\n"
        
        prompt = f"""
        You are an AI assistant helping a user understand a website's content.
        
        Website Context:
        {content}
        
        Conversation History:
        {history_prompts}
        
        User Question: {query}
        
        Return a JSON object with:
        {{
            "agent_response": "Your helpful answer here.",
            "context_sources": ["List of direct quotes or short summaries of the specific sections used to answer"]
        }}
        """
        
        response = self.model.generate_content(prompt)
        try:
            return json.loads(response.text)
        except:
             text = response.text.replace("```json", "").replace("```", "").strip()
             return json.loads(text)
