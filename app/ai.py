import os
import json
import sqlite3
from typing import List, Optional, Dict
from .models import CompanyInfo, ExtractedAnswer, ChatMessage

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import START, MessagesState, StateGraph

class AIService:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Groq API Key is missing. Please set GROQ_API_KEY in your .env file.")
        
        # Initialize Groq Model
        # Using Llama3-70b-8192 for high quality and speed
        self.llm = ChatGroq(
            model_name="llama3-70b-8192",
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
        prompt_text = f"""
        Analyze the following website content and extract key business insights.
        
        Website Content:
        {content[:15000]}  # Truncate to avoid context limits if necessary, though Groq handles large contexts well.
        
        Return a valid JSON object with this exact structure (do not include markdown formatting like ```json):
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
        
        # Use simple invoke
        response = self.llm.invoke([
            SystemMessage(content="You are a business intelligence AI that outputs exclusively in valid JSON."),
            HumanMessage(content=prompt_text)
        ])
        
        try:
            text = response.content.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except Exception as e:
            # Fallback for partial JSON or errors
             raise ValueError(f"Failed to parse AI response: {str(e)} | Raw: {text[:100]}...")

    async def chat_interaction(self, content: str, query: str, thread_id: str, history: Optional[List[ChatMessage]] = None) -> dict:
        """New chat logic using LangGraph with SQLite persistence."""
        
        config = {"configurable": {"thread_id": thread_id}}
        
        # Use async context manager for the saver
        async with AsyncSqliteSaver.from_conn_string(self.db_path) as saver:
            graph = self.workflow.compile(checkpointer=saver)
            
            # Check if we have an existing state for this thread
            state = await graph.aget_state(config)
            
            messages = []
            
            # If no history exists in DB for this thread, initialize with system context
            if not state or not state.values.get("messages"):
                system_msg = SystemMessage(content=f"You are an AI assistant helping a user understand a website's content.\n\nWebsite Context:\n{content}")
                messages.append(system_msg)
                
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
        
        # Prepare response format to match original
        return {
            "agent_response": last_msg.content,
            "context_sources": ["Website content analysis stored in thread memory"]
        }

