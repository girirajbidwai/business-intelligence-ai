import os
import json
import sqlite3
from typing import List, Optional, Dict
from .models import CompanyInfo, ExtractedAnswer, ChatMessage

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import START, MessagesState, StateGraph
import logging

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Groq API Key is missing. Please set GROQ_API_KEY in your .env file.")
        
        # Initialize Groq Model
        # using configurable model name, defaulting to Llama3-70b-8192
        model_name = os.getenv("GROQ_MODEL", "llama3-70b-8192")
        self.llm = ChatGroq(
            model_name=model_name,
            groq_api_key=api_key,
            temperature=0
        )
        
        # LangGraph Setup
        workflow = StateGraph(MessagesState)
        
        def call_model(state: MessagesState):
            # The last message might contains context if we inject it there
            # or we can rely on the system message being present in the history
            response = self.llm.invoke(state["messages"])
            return {"messages": [response]}
            
        workflow.add_node("agent", call_model)
        workflow.add_edge(START, "agent")
        
        # Persistence layer path
        # In serverless environments like Netlify (AWS Lambda), we use /tmp for writable SQLite
        # On Render with a Disk, we use /data/checkpoints.sqlite if available, else /tmp or local
        if os.getenv("RENDER"):
             if os.path.exists("/data"):
                 self.db_path = "/data/checkpoints.sqlite"
             else:
                 self.db_path = "/tmp/checkpoints.sqlite" # Fallback for free tier (ephemeral)
        elif os.getenv("NETLIFY") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
            self.db_path = "/tmp/checkpoints.sqlite"
        else:
            self.db_path = "checkpoints.sqlite"
        self.workflow = workflow

    async def analyze_content(self, content: str, questions: Optional[List[str]] = None) -> dict:
        """Analysis logic using Groq (Llama 3) with strict JSON prompting."""
        prompt_text = f"""Analyze the following website content and extract key business insights.

Website Content:
{content[:15000]}

Return ONLY a raw JSON object — no markdown fences, no explanation, no text before or after the JSON.
Use this exact structure:
{{
    "company_info": {{
        "industry": "Primary industry",
        "company_size": "Estimated size (small/medium/large or employee count)",
        "location": "Headquarters location or 'Unknown'",
        "core_products_services": ["product1", "product2"],
        "unique_selling_proposition": "What makes them stand out",
        "target_audience": "Primary customer demographic",
        "overall_sentiment": "Positive/Neutral/Professional",
        "contact_info": {{
            "email": "email or null",
            "phone": "phone or null",
            "social_media": {{"linkedin": "url or null", "twitter": "url or null", "facebook": "url or null", "instagram": "url or null"}}
        }}
    }},
    "extracted_answers": [
        {{"question": "question text", "answer": "concise answer"}}
    ]
}}

Additional Questions to answer:
{json.dumps(questions) if questions else "None"}"""
        
        logger.info("Invoking LLM for website content analysis.")
        response = self.llm.invoke([
            SystemMessage(content="You are a business intelligence AI. Output ONLY valid JSON. No markdown, no explanation, no preamble."),
            HumanMessage(content=prompt_text)
        ])
        
        try:
            text = response.content.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except Exception as e:
            # Fallback for partial JSON or errors
             logger.error(f"Failed to parse AI response: {str(e)} | Raw: {text[:200]}...")
             raise ValueError(f"Failed to parse AI response: {str(e)} | Raw: {text[:100]}...")

    async def chat_interaction(self, content: str, query: str, thread_id: str, history: Optional[List[ChatMessage]] = None) -> dict:
        """Chat logic using LangGraph with SQLite persistence and optimized prompts."""
        logger.info(f"Processing chat query using thread_id: {thread_id}")
        config = {"configurable": {"thread_id": thread_id}}
        
        # Truncate website content to keep the context window focused
        trimmed_content = content[:6000] if len(content) > 6000 else content
        
        # Highly optimized system prompt to reduce garbage output
        system_prompt = (
            "You are a concise business intelligence assistant. "
            "Your ONLY job is to answer questions about the website content provided below.\n\n"
            "RULES:\n"
            "1. Be concise — answer in 2-4 sentences unless the user asks for detail.\n"
            "2. Stay grounded — ONLY use information from the website content below. "
            "If the answer is not in the content, say \"This information is not available on the website.\"\n"
            "3. No filler — do not repeat the question, do not add unnecessary preambles like "
            "\"Sure!\", \"Great question!\", or \"Based on the website content...\".\n"
            "4. Use bullet points for lists of 3+ items.\n"
            "5. Do not hallucinate or speculate beyond what the content states.\n"
            "6. If asked to compare or analyze, base it strictly on the provided content.\n\n"
            f"--- WEBSITE CONTENT ---\n{trimmed_content}\n--- END CONTENT ---"
        )
        
        # Use async context manager for the saver
        async with AsyncSqliteSaver.from_conn_string(self.db_path) as saver:
            graph = self.workflow.compile(checkpointer=saver)
            
            # Check if we have an existing state for this thread
            state = await graph.aget_state(config)
            
            messages = []
            
            # If no history exists in DB for this thread, initialize with system context
            if not state or not state.values.get("messages"):
                messages.append(SystemMessage(content=system_prompt))
                
                # If historical messages were passed in the request (legacy support), add them
                if history:
                    for msg in history:
                        if msg.role == "user":
                            messages.append(HumanMessage(content=msg.content))
                        else:
                            messages.append(AIMessage(content=msg.content))
            
            # Add the current user query
            messages.append(HumanMessage(content=query))
            
            # Run the graph
            result = await graph.ainvoke({"messages": messages}, config)
        
        # Extract the last message which is the agent's response
        last_msg = result["messages"][-1]
        
        return {
            "agent_response": last_msg.content,
            "context_sources": ["Website content analysis stored in thread memory"]
        }

