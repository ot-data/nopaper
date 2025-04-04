import asyncio
import json
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple memory store
memory_store: Dict[str, List[Dict]] = {}

def get_previous_question(session_id: str) -> Optional[str]:
    if session_id in memory_store and memory_store[session_id]:
        return memory_store[session_id][-1]["question"]
    return None

def add_interaction(session_id: str, question: str, answer: str):
    if session_id not in memory_store:
        memory_store[session_id] = []
    memory_store[session_id].append({"question": question, "answer": answer})
    # Keep only the last 5 interactions
    if len(memory_store[session_id]) > 5:
        memory_store[session_id].pop(0)

def is_memory_query(query: str) -> bool:
    query = query.lower().strip()
    memory_triggers = [
        "previous question", "last question", "what did i ask",
        "what was my question", "my previous", "earlier question"
    ]
    return any(trigger in query for trigger in memory_triggers)

@app.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection established")

    while True:
        try:
            # Receive client message
            data = await websocket.receive_json()
            query = data.get('query', '')
            session_id = data.get('session_id', 'default')

            print(f"Received query: '{query}' with session_id: {session_id}")

            # Handle memory queries
            if is_memory_query(query):
                previous_question = get_previous_question(session_id)
                print(f"Previous question: {previous_question}")

                if previous_question:
                    response_text = f"Your previous question was: '{previous_question}'"
                else:
                    response_text = "You haven't asked any questions yet in this session."

                await websocket.send_json({"type": "response", "content": response_text})
                add_interaction(session_id, query, response_text)
            else:
                # For non-memory queries, just echo back a response
                response_text = f"You asked: {query}"
                await websocket.send_json({"type": "response", "content": response_text})
                add_interaction(session_id, query, response_text)

        except Exception as e:
            print(f"WebSocket error: {e}")
            break

@app.get("/")
async def root():
    return {"message": "Memory test server is running. Connect to /chat"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)  # Use a different port to avoid conflicts
