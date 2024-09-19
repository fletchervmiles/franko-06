import asyncio
import websockets
import os

async def test_connection():
    uri = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"
    auth_key = os.environ.get("ASSEMBLYAI_API_KEY")
    try:
        async with websockets.connect(uri, extra_headers={"Authorization": auth_key}) as websocket:
            print("Connection to AssemblyAI established successfully.")
            await websocket.send("Test message")
            response = await websocket.recv()
            print(f"Received response: {response}")
    except Exception as e:
        print(f"Failed to connect to AssemblyAI: {e}")

asyncio.get_event_loop().run_until_complete(test_connection())
