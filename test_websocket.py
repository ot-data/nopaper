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

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    while True:
        try:
            # Receive message
            data = await websocket.receive_text()
            
            # Echo the message back
            await websocket.send_text(f"You said: {data}")
            
        except Exception as e:
            print(f"WebSocket error: {e}")
            break

@app.get("/")
async def root():
    return {"message": "WebSocket server is running. Connect to /ws"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
