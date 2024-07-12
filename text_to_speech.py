    

import os
import requests
import shutil
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Body, WebSocket
from vonage import Client
from uuid import uuid4
from pydantic import BaseModel, Field
from datetime import datetime
import asyncio

# Load environment variables
load_dotenv()

app = FastAPI()

# Vonage credentials
VONAGE_APPLICATION_ID = os.environ.get("VONAGE_APPLICATION_ID")
VONAGE_APPLICATION_PRIVATE_KEY_PATH = os.environ.get("VONAGE_APPLICATION_PRIVATE_KEY_PATH")
VONAGE_NUMBER = os.environ.get("VONAGE_NUMBER")
TO_NUMBER = os.environ.get("TO_NUMBER")

# Initialize Vonage client
client = Client(
    application_id=VONAGE_APPLICATION_ID,
    private_key=VONAGE_APPLICATION_PRIVATE_KEY_PATH,
)

class CallStatus(BaseModel):
    headers: dict
    from_: str = Field(alias="from")
    to: str
    uuid: str
    conversation_uuid: str
    status: str
    direction: str
    timestamp: str

class TextToSpeech:
    # Set your Deepgram API Key and desired voice model
    DG_API_KEY = os.getenv("DEEPGRAM_API_KEY")
    MODEL_NAME = "aura-asteria-en"  # Example model name, change as needed

    @staticmethod
    def is_installed(lib_name: str) -> bool:
        lib = shutil.which(lib_name)
        return lib is not None

    def generate_speech(self, text):
        DEEPGRAM_URL = f"https://api.deepgram.com/v1/speak?model={self.MODEL_NAME}&performance=some&encoding=linear16&sample_rate=16000"
        headers = {
            "Authorization": f"Token {self.DG_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "text": text
        }

        response = requests.post(DEEPGRAM_URL, headers=headers, json=payload)
        response.raise_for_status()

        return response.content

@app.post("/call")
async def make_outgoing_call():
    try:
        call_id = str(uuid4())
        print(f"Call initiated with call_id: {call_id}")

        response = client.voice.create_call({
            'to': [{'type': 'phone', 'number': TO_NUMBER}],
            'from': {'type': 'phone', 'number': VONAGE_NUMBER},
            'ncco': [
                {
                    'action': 'connect',
                    'endpoint': [
                        {
                            'type': 'websocket',
                            'uri': f'wss://c78b-146-70-186-190.ngrok-free.app/ws?call_id={call_id}',
                            'content-type': 'audio/l16;rate=16000',
                            'headers': {
                                'language': 'en-GB',
                                'caller-id': VONAGE_NUMBER
                            }
                        }
                    ]
                }
            ],
            'event_url': [f'https://c78b-146-70-186-190.ngrok-free.app/vonage_call_status?call_id={call_id}'],
            'event_method': 'POST'
        })

        return {"message": "Call initiated", "call_id": call_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/vonage_call_status")
async def handle_vonage_call_status(call_id: str = Query(...), call_status: CallStatus = Body(...)):
    print(f"Received status: {call_status.status}, call_id: {call_id}")
    return {"message": "Status update received"}


async def listen(vonage_websocket: WebSocket, audio_data):
    print(f"{datetime.now()}: listen task started")
    samples = bytearray()
    try:
        # Extend the samples array with the audio data
        samples.extend(audio_data)

        # Set the buffer size to 6 chunks of 20ms audio (320 * 2 bytes per chunk)
        buffer_size = int(2 / 0.02)

        # Introduce a pre-buffering delay (e.g., 500ms)
        await asyncio.sleep(0.1)

        while len(samples) >= 320 * 2:
            pre_send_time = datetime.now()
            for i in range(buffer_size):
                chunk = samples[i*320*2:(i+1)*320*2]
                await vonage_websocket.send_bytes(chunk)
            post_send_time = datetime.now()
            print(f"{datetime.now()}: Sent batch to Vonage, took {(post_send_time - pre_send_time).total_seconds()} seconds")
            samples = samples[buffer_size*320*2:]

        # Send the remaining audio data in smaller chunks
        for i in range(0, len(samples), 320*2):
            chunk = samples[i:i+320*2]
            await vonage_websocket.send_bytes(chunk)
            await asyncio.sleep(0.017)  # Wait for 20ms to simulate real-time streaming

    except Exception as e:
        print(f"{datetime.now()}: Error in listen task: {e}")
    print(f"{datetime.now()}: listen task completed")



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, call_id: str = Query(...)):
    await websocket.accept()
    print(f"WebSocket connection opened for call_id: {call_id}")

    try:
        # Generate speech using TextToSpeech
        tts = TextToSpeech()
        text = "Hey, how are you?"
        audio_data = tts.generate_speech(text)

        # Send the audio data to the connected call
        await listen(websocket, audio_data)

        # Keep the WebSocket connection open for further communication if needed
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.receive":
                if "text" in message:
                    text_data = message["text"]
                    print(f"Received text message: {text_data}")
                    # Handle text message
                elif "bytes" in message:
                    bytes_data = message["bytes"]
                    # print(f"Received bytes message: {bytes_data}")
                    # Handle bytes message
            elif message["type"] == "websocket.disconnect":
                print("WebSocket disconnected")
                break

    except Exception as e:
        print(f"Error in WebSocket endpoint: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)