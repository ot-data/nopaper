import asyncio
import websockets
import json
import time
import uuid

async def test_session_id_management():
    """Test the session ID management in the WebSocket server."""
    print("\n=== Testing Session ID Management ===\n")
    
    # Test 1: Initial connection without session ID
    print("\n--- Test 1: Initial Connection without Session ID ---")
    session_id = None
    
    # Connect to the WebSocket server
    print("Connecting to WebSocket server...")
    async with websockets.connect("ws://localhost:8000/chat") as websocket:
        print("Connection established!")
        
        # Send a message without session ID
        message = "Hello, this is a test message"
        message_data = {
            'message_id': 0,
            'query': message,
            'session_id': session_id
        }
        
        # Send the message
        await websocket.send(json.dumps(message_data))
        print(f"Message sent without session ID!")
        
        # Collect responses and extract session ID
        while True:
            response = await websocket.recv()
            data = json.loads(response)
            print(f"Received response: {data}")
            
            # Extract session ID from response
            if 'session_id' in data:
                session_id = data['session_id']
                print(f"Received session ID: {session_id}")
            
            # Check if this is the last chunk
            if data.get('is_last', False):
                break
    
    print(f"Test 1 completed. Session ID: {session_id}")
    
    # Wait a bit before reconnecting
    await asyncio.sleep(1)
    
    # Test 2: Reconnect with the received session ID
    print("\n--- Test 2: Reconnection with Session ID ---")
    
    # Connect to the WebSocket server again
    print("Reconnecting to WebSocket server...")
    async with websockets.connect("ws://localhost:8000/chat") as websocket:
        print("Connection re-established!")
        
        # Send a message with the session ID
        message = "This is a second message with the same session ID"
        message_data = {
            'message_id': 1,
            'query': message,
            'session_id': session_id
        }
        
        # Send the message
        await websocket.send(json.dumps(message_data))
        print(f"Message sent with session ID: {session_id}")
        
        # Collect responses
        received_session_id = None
        while True:
            response = await websocket.recv()
            data = json.loads(response)
            print(f"Received response: {data}")
            
            # Extract session ID from response
            if 'session_id' in data:
                received_session_id = data['session_id']
            
            # Check if this is the last chunk
            if data.get('is_last', False):
                break
        
        # Verify session ID consistency
        if received_session_id == session_id:
            print(f"✅ Session ID consistency verified: {session_id}")
        else:
            print(f"❌ Session ID mismatch! Original: {session_id}, Received: {received_session_id}")
    
    # Wait a bit before the memory test
    await asyncio.sleep(1)
    
    # Test 3: Memory persistence test
    print("\n--- Test 3: Memory Persistence Test ---")
    
    # Connect to the WebSocket server again
    print("Reconnecting to WebSocket server...")
    async with websockets.connect("ws://localhost:8000/chat") as websocket:
        print("Connection re-established for memory test!")
        
        # Send a memory query with the session ID
        message = "What was my previous question?"
        message_data = {
            'message_id': 2,
            'query': message,
            'session_id': session_id
        }
        
        # Send the message
        await websocket.send(json.dumps(message_data))
        print(f"Memory query sent with session ID: {session_id}")
        
        # Collect responses
        full_response = ""
        while True:
            response = await websocket.recv()
            data = json.loads(response)
            
            if data.get('type') == 'response':
                content = data.get('content', '')
                full_response += content
                print(f"Received chunk: {content}")
            
            # Check if this is the last chunk
            if data.get('is_last', False):
                break
        
        print(f"Complete memory response: {full_response}")
        
        # Check if the response contains the previous question
        if "second message" in full_response.lower():
            print("✅ Memory persistence verified! Previous question was remembered.")
        else:
            print("❌ Memory persistence failed! Previous question was not remembered.")
    
    print("\n=== Session ID Management Testing Completed ===")

if __name__ == "__main__":
    asyncio.run(test_session_id_management())
