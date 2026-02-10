import os
import json
import sqlite3
from typing import List, Optional, Dict
from .models import CompanyInfo, ExtractedAnswer, ChatMessage
from .vector_store import VectorStoreManager

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import START, MessagesState, StateGraph
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Groq API Key is missing. Please set GROQ_API_KEY in your .env file.")
        
        # Initialize Groq Model
        model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        self.llm = ChatGroq(
            model_name=model_name,
            groq_api_key=api_key,
            temperature=0
        )
        
        self.vector_store = VectorStoreManager()
        
        # LangGraph Setup
        workflow = StateGraph(MessagesState)
        
        def call_model(state: MessagesState):
            response = self.llm.invoke(state["messages"])
            return {"messages": [response]}
            
        workflow.add_node("agent", call_model)
        workflow.add_edge(START, "agent")
        
        # Persistence layer path
        if os.getenv("RENDER"):
             if os.path.exists("/data"):
                 self.db_path = "/data/checkpoints.sqlite"
             else:
                 self.db_path = "/tmp/checkpoints.sqlite"
        elif os.getenv("NETLIFY") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
            self.db_path = "/tmp/checkpoints.sqlite"
        else:
            self.db_path = "checkpoints.sqlite"
        self.workflow = workflow

    async def analyze_content(self, website_data: List[Dict[str, str]], questions: Optional[List[str]] = None) -> dict:
        """Analysis logic using Groq (Llama 3) with strict JSON prompting."""
        # For general analysis, we mostly use the homepage content but can include snippets from others
        # To keep it simple for the initial summary, we use the first page (usually homepage)
        main_content = website_data[0]["content"] if website_data else ""
        
        # Index everything into Pinecone for RAG
        if website_data:
            try:
                await self.vector_store.index_website_content(website_data)
            except Exception as e:
                logger.error(f"Failed to index content: {e}")

        prompt_text = f"""Analyze the following website content and extract key business insights.

Website Content (Homepage):
{main_content[:15000]}

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
             logger.error(f"Failed to parse AI response: {str(e)} | Raw: {text[:200]}...")
             raise ValueError(f"Failed to parse AI response: {str(e)} | Raw: {text[:100]}...")

    async def chat_interaction(self, url: str, query: str, thread_id: str, history: Optional[List[ChatMessage]] = None) -> dict:
        """Chat logic using LangGraph with Pinecone RAG and SQLite persistence."""
        logger.info(f"Processing chat query using thread_id: {thread_id}")
        config = {"configurable": {"thread_id": thread_id}}
        
        # Retrieve context from Pinecone dedicated DB
        context = self.vector_store.query_context(url, query)
        
        if not context:
            # Fallback if Pinecone is not available or has no data
            context = "No specific website content found for this query."
            context_sources = []
        else:
            # Extract source URLs for display
            context_sources = list(set([line.split("Source [")[1].split("]")[0] for line in context.splitlines() if "Source [" in line]))

        # Highly optimized system prompt for strict grounding
        system_prompt = (
            "You are a strict business intelligence assistant. "
            "Your ONLY source of information is the PROVIDED CONTEXT below. "
            "You are FORBIDDEN from using any pre-trained knowledge about this company or any other external information.\n\n"
            "STRICT RULES:\n"
            "1. Grounding: ONLY answer using the provided context. If the answer is not explicitly stated in the context, "
            "say: \"I am sorry, but the provided website content does not contain information to answer this question.\"\n"
            "2. Conciseness: Answer in 2-4 sentences max unless detail is specifically requested.\n"
            "3. Preamble: DO NOT start with \"Based on the context...\" or \"Sure!\". Start directly with the answer.\n"
            "4. Sources: If multiple sources provide information, synthesize them.\n"
            "5. Navigation: Mention relevant URLs from the context if they directly support your answer.\n\n"
            f"--- PROVIDED CONTEXT From Website ---\n{context}\n--- END CONTEXT ---"
        )
        
        # Use async context manager for the saver
        async with AsyncSqliteSaver.from_conn_string(self.db_path) as saver:
            graph = self.workflow.compile(checkpointer=saver)
            
            # Check if we have an existing state for this thread
            state = await graph.aget_state(config)
            
            messages = []
            
            # If no history exists in DB for this thread, initialize with system context
            # NOTE: We update the system prompt EACH time with the new retrieved context for the current query
            # However, in LangGraph, we might want to keep the system prompt stable or update it.
            # To ensure the LATEST context is used, we inject it as a system message.
            
            messages.append(SystemMessage(content=system_prompt))
            
            if state and state.values.get("messages"):
                # Append existing history (excluding previous system messages)
                for msg in state.values["messages"]:
                    if not isinstance(msg, SystemMessage):
                        messages.append(msg)
            elif history:
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
            "context_sources": context_sources if context_sources else ["Website Content"]
        }


