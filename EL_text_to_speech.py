import os
import requests
import time
import logging
from dotenv import load_dotenv
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
    # Set your ElevenLabs API Key and desired voice ID
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    VOICE_ID = "OYTbf65OHHFELVut7v2H"  # Replace with the desired voice ID

    def generate_speech(self, text, save_path=None):
        start_time = time.time()
        ELEVENLABS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{self.VOICE_ID}?optimize_streaming_latency=3&output_format=pcm_16000"
        headers = {
            "xi-api-key": self.ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            # "model_id": "eleven_turbo_v2_5",
            "model_id": "eleven_turbo_v2",
            "text": text,
            "voice_settings": {
                "similarity_boost": 1,
                "stability": 1
            }
        }
        try:
            response = requests.post(ELEVENLABS_URL, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            audio_content = response.content
            print(f"Time taken for ElevenLabs API request: {time.time() - start_time} seconds")

            if save_path:
                self.save_audio(audio_content, save_path)

            return audio_content
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTPError during ElevenLabs API request: {e.response.status_code} {e.response.text}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error during ElevenLabs API request: {e}")
        print(f"Failed to generate speech for text: {text}")
        return None

    def save_audio(self, audio_content, save_path):
        try:
            with open(save_path, 'wb') as f:
                f.write(audio_content)
            print(f"Raw audio saved to {save_path}")
        except Exception as e:
            logging.error(f"Error saving audio file: {e}")



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
                            'uri': f'wss://1fed-184-82-29-142.ngrok-free.app/ws?call_id={call_id}',
                            'content-type': 'audio/l16;rate=16000',
                            'headers': {
                                'language': 'en-GB',
                                'caller-id': VONAGE_NUMBER
                            }
                        }
                    ]
                }
            ],
            'event_url': [f'https://1fed-184-82-29-142.ngrok-free.app/vonage_call_status?call_id={call_id}'],
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
        text = """Understood. <break time="0.5s" /> allow me a brief moment to think.
        
        <break time="1s" /> Okay<break time="0.7s" />."""
        
        save_path = f"audio_{call_id}.raw"
        audio_data = tts.generate_speech(text, save_path)

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