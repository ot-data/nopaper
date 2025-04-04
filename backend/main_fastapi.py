import asyncio
import json
import os
from typing import Dict, Optional
import uvicorn
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from litellm import acompletion
from pydantic import BaseModel
from starlette.websockets import WebSocketState,WebSocketDisconnect
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import get_full_config, set_aws_credentials, PORT
from bedrock_retriever import EnhancedBedrockRetriever
from function_registry import function_registry
from memory import ConversationMemory
from institution_manager import InstitutionManager
from utils import (
    load_config,
    is_memory_query, is_relevant_query,
    get_cached_answer, cache_answer
)

# Load configuration
try:
    config = load_config()
    set_aws_credentials()
except Exception as e:
    print(f"Error loading configuration: {e}")
    config = {}

cache: Dict[str, Dict] = {}
memory_store: Dict[str, ConversationMemory] = {}

# Get or create memory for a session
def get_memory(session_id: str) -> ConversationMemory:
    if session_id not in memory_store:
        memory_store[session_id] = ConversationMemory(max_history=5)
    return memory_store[session_id]

# Request model for HTTP endpoint
class ChatRequest(BaseModel):
    query: str
    personal_info: Optional[Dict] = None
    institution_id: Optional[str] = None
    session_id: Optional[str] = None

import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

def get_personal_info_context(personal_info: Optional[Dict] = None) -> str:
    if not personal_info:
        return "No personal information provided."
    context = "Personal Information:\n"
    for key, value in personal_info.items():
        context += f"- {key}: {value}\n"
    return context


# Special queries handling
SPECIAL_QUERIES = [
    "i want to raise a query",
    "can i raise a query",
    "can i raise a ticket",
    "can i connect to someone",
    "can i speak to the counsellor",
    "How can I track my application status?"
]

def normalize_query(query: str) -> str:
    """Normalize query for comparison"""
    query = re.sub(r'[^\w\s]', '', query)
    return ' '.join(query.strip().lower().split())

NORMALIZED_SPECIAL_QUERIES = {normalize_query(q) for q in SPECIAL_QUERIES}

# Core response generation logic with streaming
async def generate_response(query: str, personal_info: Optional[Dict] = None, institution_id: Optional[str] = None, session_id: str = "default"):
    # Get or create memory for this session
    memory = get_memory(session_id)
    retriever = EnhancedBedrockRetriever(config)

    normalized = normalize_query(query)
    if normalized in NORMALIZED_SPECIAL_QUERIES:
        memory.add_interaction(query, "{{RAISE_QUERY}}")
        yield {"type": "response", "content": "{{RAISE_QUERY}}"}
        return


    if is_memory_query(query):
        previous_question = memory.get_previous_question()
        print(f"DEBUG - Previous question retrieved: {previous_question}")
        print(f"DEBUG - Memory history: {memory.conversation_history}")

        if previous_question:
            response_text = f"Your previous question was: '{previous_question}'"
        else:
            response_text = "You haven't asked any questions yet in this session."

        yield {"type": "response", "content": response_text}
        memory.add_interaction(query, response_text)
        return



    # Check cache for existing answers
    cached_answer = get_cached_answer(query, cache, config)
    if cached_answer:
        yield {"type": "response", "content": cached_answer}
        memory.add_interaction(query, cached_answer)
        return

    # Get institution domain for filtering references
    institution_manager = InstitutionManager()
    institution_config = institution_manager.get_institution_config(institution_id)
    institution_domain = None
    if institution_config and "website" in institution_config:
        # Extract domain from website URL (e.g., "www.lpu.in" -> "lpu.in")
        website = institution_config["website"]
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(website)
            institution_domain = parsed_url.netloc
            # Remove www. prefix if present
            if institution_domain.startswith("www."):
                institution_domain = institution_domain[4:]
        except:
            institution_domain = "lpu.in"  # Default fallback

    # Retrieve context from knowledge base
    retrieval_response = retriever.retrieve(query, advanced=True)
    retrieved_content, _ = retriever.format_retrieval_results(retrieval_response)
    print(f"retrieved_content {retrieved_content}")
    references_raw = retriever.get_specific_source_urls(retrieval_response, institution_domain=institution_domain)

    # Build context for the prompt
    context = memory.get_context()
    personal_info_context = get_personal_info_context(personal_info)

    dynamic_template = institution_manager.get_processed_prompt(institution_id)
    print(f"Using institution_id: {institution_id}")
    print(f"Institution config: {institution_config}")

    prompt = f"""
    # Conversation History
    {context}

    # Personal Information
    {personal_info_context}

    # Retrieved Knowledge
    {retrieved_content}

    # Institution-specific Template
    {dynamic_template}

    Please answer: "{query}"
    """

    # Stream response from the AI model
    try:
        response = await acompletion(
            model=f"bedrock/{config['aws']['bedrock_model']}",
            messages=[
                {"role": "system", "content": "You are an LPU career guidance expert. Follow instructions precisely."},
                {"role": "user", "content": prompt}
            ],
            # tools=function_registry.get_function_call_schema(),
            stream=True
        )

        full_answer = ""
        async for chunk in response:
            if chunk and "choices" in chunk and chunk["choices"]:
                delta = chunk["choices"][0].get("delta", {}).get("content", "")
                if delta:
                    full_answer += delta
                    yield {"type": "response", "content": delta}

        # Add references if available
        if references_raw:
            yield {"type": "response", "content": f"\n\n---\n**References:**\n{references_raw}"}

        # Cache and store the response
        cache_answer(query, full_answer, cache, config)

        # Add to memory and print debug info
        print(f"DEBUG - Adding to memory: Q: {query}, A: {full_answer[:50]}...")
        memory.add_interaction(query, full_answer)
        print(f"DEBUG - Memory after adding: {len(memory.conversation_history)} entries")

    except Exception as e:
        error_msg = f"Error processing query: {str(e)}"
        yield {"type": "error", "content": error_msg}

# WebSocket endpoint for real-time chat
@app.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Generate a unique session ID for this WebSocket connection
    session_id = str(id(websocket))
    print(f"DEBUG - New WebSocket connection established with session_id: {session_id}")

    while True:
        try:
            # Receive client message
            data = await websocket.receive_json()
            query = data.get('query')
            personal_info = data.get('personal_info')
            institution_id = data.get('institution_id')

            # Use client-provided session ID if available, otherwise use the WebSocket ID
            client_session_id = data.get('session_id')
            effective_session_id = client_session_id if client_session_id else session_id

            print(f"DEBUG - WebSocket received query: '{query}' with session_id: {effective_session_id}")

            if not query:
                await websocket.send_json({"type": "error", "content": "No query provided"})
                continue

            # Stream the response with the session ID
            async for response in generate_response(query, personal_info, institution_id, effective_session_id):
                await websocket.send_json(response)

        except WebSocketDisconnect:
            print("WebSocket disconnected")
            break
        except Exception as e:
            print(f"WebSocket error: {e}")
            if websocket.state == WebSocketState.CONNECTED:
                await websocket.close()
            break

# HTTP endpoint for chat
@app.post("/chat")
async def http_chat(request: ChatRequest):
    responses = []
    # For HTTP requests, use provided session_id or generate one
    effective_session_id = request.session_id if request.session_id else "http_" + str(hash(str(request.personal_info) + str(request.institution_id)))

    print(f"DEBUG - HTTP request received: '{request.query}' with session_id: {effective_session_id}")

    async for response in generate_response(request.query, request.personal_info, request.institution_id, effective_session_id):
        responses.append(response)
    return {"responses": responses}

# Run the application
if __name__ == "__main__":
    # Use PORT from config module
    uvicorn.run(app, host="0.0.0.0", port=PORT)