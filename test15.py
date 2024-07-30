"""
This is test02.py file
"""

from fastapi import FastAPI, HTTPException, Query, Body, WebSocket, Request, WebSocketDisconnect
from starlette.websockets import WebSocketState
from websockets.exceptions import ConnectionClosedError, WebSocketException
from vonage import Client as VonageClient, Voice
import os
import io
import wave
from dotenv import load_dotenv
from uuid import uuid4
from pydantic import BaseModel, Field
import asyncio
# from salesgpt.logger import time_logger, logger
from salesgpt.salesgptapi01 import SalesGPTAPI
import redis
import json
from pprint import pprint
from enum import Enum
import requests
import time
from supabase import create_client as create_supabase_client, Client as SupabaseClient
from datetime import datetime, timedelta
import shutil
import logging
import tracemalloc
import traceback
import psutil
import random
import aiohttp
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)



logging.getLogger("requests").setLevel(logging.WARNING)
logging.basicConfig(level=logging.WARNING)  # Set global logging level
logging.getLogger().setLevel(logging.WARNING)  # Set root logger level

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(debug=True)

# API configuration and routes
CONFIG_PATH = "examples/example_agent_setup.json"
# print(f"Config path: {CONFIG_PATH}")

# Create an instance of SalesGPTAPI
sales_api = SalesGPTAPI(config_path=CONFIG_PATH, verbose=False)

# Load environment variables
load_dotenv()
tracemalloc.start()
app = FastAPI()

# Supabase URL, API key
supabase_url: str = os.environ.get("SUPABASE_URL")
supabase_key: str = os.environ.get("SUPABASE_KEY")

# Initialize Supabase
supabase: SupabaseClient = create_supabase_client(supabase_url, supabase_key)

# # Configure logging
# logging.basicConfig(level=logging.ERROR)
# logger = logging.getLogger(__name__)

# Create a dictionary to store SharedData instances for each call
shared_data_dict = {}
state_machines = {}

# Initialize Redis
redis_host = os.getenv('REDIS_HOST')
redis_port = os.getenv('REDIS_PORT')
redis_db = os.getenv('REDIS_DB')
r = redis.Redis(host=redis_host, port=redis_port, db=redis_db)

# Vonage credentials
VONAGE_APPLICATION_ID = os.environ.get("VONAGE_APPLICATION_ID")
VONAGE_APPLICATION_PRIVATE_KEY_PATH = os.environ.get("VONAGE_APPLICATION_PRIVATE_KEY_PATH")
VONAGE_NUMBER = os.environ.get("VONAGE_NUMBER")
TO_NUMBER = os.environ.get("TO_NUMBER")

# Initialize Vonage client
vonage_client = VonageClient(
    application_id=VONAGE_APPLICATION_ID,
    private_key=VONAGE_APPLICATION_PRIVATE_KEY_PATH,
)
voice = Voice(vonage_client)

class CallStatus(BaseModel):
    headers: dict
    from_: str = Field(alias="from")
    to: str
    uuid: str
    conversation_uuid: str
    status: str
    direction: str
    timestamp: str

class CallState(Enum):
    CALL_SETUP = "CALL_SETUP"
    GENERATE_FRANKO_RESPONSE = "GENERATE_FRANKO_RESPONSE"
    LISTEN_FOR_USER_RESPONSE = "LISTEN_FOR_USER_RESPONSE"


class SharedData:
    def __init__(self):
        self._data = {}
        self.websocket = None
        self.websocket_ready = asyncio.Event()
        self.call_completed = False
        self.state_machine = None
        self.is_reconnecting = False
        self.reconnection_attempts = 0
        
        # These are for the listening functionality
        self.transcript_parts = []
        self.last_word_time = None
        self.last_no_word_time = None



    def set_websocket(self, websocket):
        self.websocket = websocket

    def get_websocket(self):
        return self.websocket


    def set_state_machine(self, state_machine):
        self.state_machine = state_machine
        # print("State machine set.")


    # These four methods are for the listening functionality
    def add_part(self, part):
        self.transcript_parts.append(part)

    def get_full_transcript(self):
        return ' '.join(self.transcript_parts)

    def update_word_timestamp(self):
        self.last_word_time = datetime.now()
        print(f"[{self.last_word_time}] Word timestamp updated")

    def update_no_word_timestamp(self):
        self.last_no_word_time = datetime.now()
        print(f"[{self.last_no_word_time}] No word timestamp updated")


    def reset(self):
        self._data = {}
        self.websocket = None
        self.websocket_ready = asyncio.Event()
        self.call_completed = False
        self.state_machine = None

    def reset_transcripts(self):
        # These are for the listening function
        self.transcript_parts = []
        self.last_word_time = None
        self.last_no_word_time = None




class AudioManager:
    def __init__(self, websocket):
        self.websocket = websocket
        self.current_audio_task = None
        self.is_playing = asyncio.Event()
        print(f"[{datetime.now()}] AudioManager initialized")

    async def play_audio(self, audio_data, duration):
        print(f"[{datetime.now()}] play_audio called with duration: {duration}")
        if self.current_audio_task and not self.current_audio_task.done():
            print(f"[{datetime.now()}] Waiting for current audio task to complete")
            await self.current_audio_task
        self.current_audio_task = asyncio.create_task(self._play_audio(audio_data, duration))
        self.is_playing.set()
        print(f"[{datetime.now()}] New audio task created and is_playing set to True")

    async def _play_audio(self, audio_data, duration):
        print(f"[{datetime.now()}] _play_audio started")
        try:
            print(f"[{datetime.now()}] Sending audio data to websocket")
            await send_audio(self.websocket, audio_data, duration)
            print(f"[{datetime.now()}] Audio data sent, sleeping for duration: {duration}")
            await asyncio.sleep(duration)
        finally:
            self.is_playing.clear()
            print(f"[{datetime.now()}] _play_audio finished, is_playing set to False")

    async def wait_for_current_audio(self):
        if self.current_audio_task:
            print(f"[{datetime.now()}] Waiting for current audio task to complete")
            await self.current_audio_task
            print(f"[{datetime.now()}] Current audio task completed")
        else:
            print(f"[{datetime.now()}] No current audio task to wait for")

    async def is_audio_playing(self):
        is_playing = self.is_playing.is_set()
        print(f"[{datetime.now()}] Checked if audio is playing: {is_playing}")
        return is_playing




class StateMachine:
    def __init__(self, call_id, r, vonage_client, shared_data, sales_api):
        self.call_id = call_id
        self.r = r
        self.vonage_client = vonage_client
        self.shared_data = shared_data
        self.sales_api = sales_api
        self.set_state(CallState.CALL_SETUP)
        self.event_queue = asyncio.Queue()
        self.human_response_received = asyncio.Event()
        self.shared_data.set_state_machine(self)

    def get_current_state(self):
        return self.state

    def set_state(self, state):
        self.state = state
        self.shared_data.set_state_machine(self)

    async def call_setup(self):
        # print("Setting up the call...")

        # Wait until the call is answered
        while r.get(f'{self.call_id}_call_answered').decode("utf-8") == 'False':
            await asyncio.sleep(0.1)

        await self.shared_data.websocket_ready.wait()
        # print(f"WebSocket in call_setup: {self.shared_data.get_websocket()}")
        # print("WebSocket Open")

        await self.event_queue.put(CallState.GENERATE_FRANKO_RESPONSE)


    async def generate_franko_response(self):
        try:
            print(f"{datetime.now()} Generate Franko Response Begun")

            conversation_history = json.loads(self.r.get(f"{self.call_id}_conversation_history").decode("utf-8"))
            human_response = self.r.get(f'{self.call_id}_human_response')
            human_response = human_response.decode("utf-8") if human_response else "N/A"
            agent_response = self.r.get(f'{self.call_id}_agent_response')
            agent_response = agent_response.decode("utf-8") if agent_response else "N/A"

            audio_manager = AudioManager(self.shared_data.get_websocket())
            empathy_statement, extracted_response, total_duration = await generate_and_send_speech(
                audio_manager, conversation_history, human_response, agent_response
            )

            agent_name = "Franko"
            ai_message = f"{agent_name}: {empathy_statement} {extracted_response}"
            self.r.set(f'{self.call_id}_agent_response', ai_message)
            conversation_history.append(ai_message)
            self.r.set(f'{self.call_id}_conversation_history', json.dumps(conversation_history))

            asyncio.create_task(self.update_conversation_stage())

            # Wait for all audio to finish playing
            while await audio_manager.is_audio_playing():
                await asyncio.sleep(0.1)

            print(f"{datetime.now()} Generate Franko Response Returned")
            await self.event_queue.put(CallState.LISTEN_FOR_USER_RESPONSE)

        except Exception as e:
            logger.exception("An error occurred in generate_franko_response: %s", str(e))





    async def update_conversation_stage(self):
        await self.sales_api.update_conversation_stage()


    async def listen_for_user_response(self):
        print(f"{datetime.now()} Listen for User Response Begun")

        # This resets the transcripts before checking again
        self.shared_data.reset_transcripts()

        print(f"[{datetime.now()}] Entering Interviewee Response Time Checker Loop")
        while True:
            if check_for_silence(self.shared_data.last_word_time, self.shared_data.last_no_word_time):
                full_transcript = self.shared_data.get_full_transcript()
                if full_transcript:
                    print(f"Full transcript: {full_transcript}")
                    break

            await asyncio.sleep(0.1)

        print(f"[{datetime.now()}] Exiting Interviewee Response Time Checker Loop")
        self.shared_data.reset_transcripts()
        print(f"[{datetime.now()}] Transcripts Reset")

        interviewee_name = "Fletcher"
        human_input = f"{interviewee_name}: " + full_transcript.strip()
        # print(f"[{datetime.now()}] Appended Human Input: {human_input}")
        conversation_history = json.loads(self.r.get(f'{self.call_id}_conversation_history').decode("utf-8"))
        conversation_history.append(human_input)
        self.r.set(f'{self.call_id}_conversation_history', json.dumps(conversation_history))
        # print(f"Updated Conversation History: {conversation_history}")

        self.r.set(f'{self.call_id}_human_response', full_transcript.strip())
        print(f"{datetime.now()} Listen for User Response Returned")
        await self.event_queue.put(CallState.GENERATE_FRANKO_RESPONSE)



    async def listen(self):
        # print(f"{datetime.now()}: Starting to listen for states...")
        try:
            while True:
                # print(f"{datetime.now()}: Waiting for next state...")
                next_state = await self.event_queue.get()
                # Log the queue size after getting the next state)
                self.set_state(next_state)  # Update the current state

                if next_state == CallState.CALL_SETUP:
                    await self.call_setup()
                elif next_state == CallState.GENERATE_FRANKO_RESPONSE:
                    await self.generate_franko_response()

                elif next_state == CallState.LISTEN_FOR_USER_RESPONSE:
                    await self.listen_for_user_response()

                else:
                    print(f"{datetime.now()}: Received an unknown state: {next_state}")
                print(f"{datetime.now()}: State handling completed for: {next_state}")
        except Exception as e:
            print(f"{datetime.now()}: Exception in listen method: {e}")
        finally:
            print(f"{datetime.now()}: Stopped listening for states.")

    async def start(self):
        await self.call_setup()  # Start with the initial state
        await self.listen()  # Start the event loop/listener

# So this runs every 0.1 seconds
def check_for_silence(last_word_time, last_no_word_time):
    if last_word_time and last_no_word_time:
        time_diff = last_no_word_time - last_word_time
        if time_diff > timedelta(seconds=3):
            return True
            print(f"{datetime.now()}: - Interviewee Response Time Checker Loop Condition Met")
    return False


def handle_transcription(result, shared_data):
    sentence = result.channel.alternatives[0].transcript
    # print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')} - {result}")

    if result.is_final and result.channel.alternatives[0].words:
        shared_data.add_part(sentence)
        print(f"{datetime.now()}: Appending partial transcript - {sentence}")






# class TextToSpeech:
#     # Set your Deepgram API Key and desired voice model
#     DG_API_KEY = os.getenv("DEEPGRAM_API_KEY")
#     MODEL_NAME = "aura-asteria-en"  # Example model name, change as needed


#     def generate_speech(self, text):
#         start_time = time.time()
#         DEEPGRAM_URL = f"https://api.deepgram.com/v1/speak?model={self.MODEL_NAME}&performance=some&encoding=linear16&sample_rate=16000&container=none"
#         headers = {
#             "Authorization": f"Token {self.DG_API_KEY}",
#             "Content-Type": "application/json"
#         }
#         payload = {
#             "text": text
#         }

#         response = requests.post(DEEPGRAM_URL, headers=headers, json=payload)
#         response.raise_for_status()
#         print(f"Time taken for Deepgram API request: {time.time() - start_time} seconds")
        
#         duration = 2

#         return response.content, duration

# class TextToSpeech:
#     # Set your ElevenLabs API Key and desired voice ID
#     ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
#     VOICE_ID = "TSsWwtgLq1gLBwl617e4"  # Replace with the desired voice ID

#     def generate_speech(self, text):
#         # start_time = time.time()
#         ELEVENLABS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{self.VOICE_ID}?optimize_streaming_latency=3&output_format=pcm_16000"
#         headers = {
#             "xi-api-key": self.ELEVENLABS_API_KEY,
#             "Content-Type": "application/json"
#         }
#         payload = {
#             "seed": -1,
#             "model_id": "eleven_turbo_v2",
#             "text": text,
#             "voice_settings": {
#                 "similarity_boost": 0.5,
#                 "stability": 0.5
#             }
#         }

#         response = requests.post(ELEVENLABS_URL, headers=headers, json=payload)
#         response.raise_for_status()
#         # print(f"Time taken for ElevenLabs API request: {time.time() - start_time} seconds")

#         # Fixed Duration
#         duration = 5

#         return response.content, duration

class TextToSpeech:

    # Set your ElevenLabs API Key and desired voice ID
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    VOICE_ID = "OYTbf65OHHFELVut7v2H"  # Replace with the desired voice ID

    def generate_speech(self, text):
        start_time = time.time()
        ELEVENLABS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{self.VOICE_ID}?optimize_streaming_latency=3&output_format=pcm_16000"
        headers = {
            "xi-api-key": self.ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "model_id": "eleven_turbo_v2_5",
            # "model_id": "eleven_multilingual_v2",
            # "model_id": "eleven_monolingual_v1",
            "text": text,
            "voice_settings": {
                "similarity_boost": 0.5,
                "stability": 0.5
            }
        }
        try:
            response = requests.post(ELEVENLABS_URL, headers=headers, json=payload, timeout=10)  # Added timeout
            response.raise_for_status()  # This will raise an exception for HTTP error codes
            print(f"Time taken for ElevenLabs API request: {time.time() - start_time} seconds")
            return response.content, 1  # Assuming a fixed duration for simplicity
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTPError during ElevenLabs API request: {e.response.status_code} {e.response.text}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error during ElevenLabs API request: {e}")
        print(f"Failed to generate speech for text: {text}")
        return None, 0  # Indicate failure



@app.post("/call")
async def make_outgoing_call():
    try:
        call_id = str(uuid4())
        print(f"{datetime.now()}: Call initiated with call_id: {call_id}")

        # Create a new SharedData instance
        shared_data = SharedData()

        # Store the SharedData instance in the dictionary
        shared_data_dict[call_id] = shared_data

        # Store call-related data in Redis
        r.set(f'{call_id}_call_answered', 'False')
        r.set(f'{call_id}_human_response', "")
        r.set(f'{call_id}_agent_response', "")
        r.set(f'{call_id}_conversation_history', json.dumps([]))

        # Create an instance of StateMachine
        state_machine = StateMachine(call_id=call_id, r=r, vonage_client=vonage_client, shared_data=shared_data, sales_api=sales_api)

        # Set the state machine in the SharedData instance
        shared_data.set_state_machine(state_machine)

        # Store the state_machine in the dictionary
        state_machines[call_id] = state_machine

        # Start the state machine asynchronously
        asyncio.create_task(state_machine.start())
        # print(f'State machine started!')

        response = vonage_client.voice.create_call({
            'to': [{'type': 'phone', 'number': TO_NUMBER}],
            'from': {'type': 'phone', 'number': VONAGE_NUMBER},
            'ncco': [
                {
                    'action': 'record',
                    'eventUrl': [f'https://1fed-184-82-29-142.ngrok-free.app/vonage_recording?call_id={call_id}'],
                    'format': 'mp3'
                },
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
    try:
        print(f"Received status: {call_status.status}, call_id: {call_id}")
        print(f"Call details: conversation_uuid: {call_status.conversation_uuid}, timestamp: {call_status.timestamp}")
        
        if call_status.status == 'answered':
            r.set(f'{call_id}_call_answered', 'True')
            print(f"{datetime.now()}: Call answered status changed to True for call_id: {call_id}")
        
        elif call_status.status == 'completed':
            state_machine = state_machines.get(call_id)
            if state_machine:
                try:
                    print(f"{datetime.now()}: Starting termination for call_id: {call_id}")

                    # Set the call_completed flag to True
                    state_machine.shared_data.call_completed = True

                    # Delay the execution by 5 seconds
                    await asyncio.sleep(2)

                    # Clean up the SharedData instance
                    if state_machine.shared_data:
                        state_machine.shared_data.reset()
                        print(f"{datetime.now()}: SharedData instance reset.")

                    # Remove the state machine from the global dictionary if it's there
                    if call_id in state_machines:
                        del state_machines[call_id]
                        print(f"{datetime.now()}: State machine removed from global dictionary.")

                    # Delete data from Redis
                    r.delete(f'{call_id}_call_answered')
                    r.delete(f'{call_id}_human_response')
                    r.delete(f'{call_id}_agent_response')
                    r.delete(f'{call_id}_conversation_history')
                    print(f"{datetime.now()}: Redis history deleted")

                    print(f"Call terminated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                except Exception as e:
                    print(f"{datetime.now()}: Error during call termination for call_id: {call_id}: {e}")
                    # Log the exception details or send an alert notification
            else:
                print(f"{datetime.now()}: State machine not found for call_id: {call_id}")
        
        else:
            print(f"{datetime.now()}: Unhandled call status: {call_status.status} for call_id: {call_id}")
            # Log the unhandled call status or send an alert notification
        
    except Exception as e:
        print(f"{datetime.now()}: Error in handle_vonage_call_status for call_id: {call_id}: {e}")
        # Log the exception details or send an alert notification
    
    return {"message": "Status update received"}


@app.post("/vonage_recording")
async def handle_recording(request: Request, call_id: str = Query(...)):
    data = await request.json()
    recording_url = data.get('recording_url')

    if recording_url:
        try:
            shared_data = shared_data_dict.get(call_id)
            if not shared_data:
                raise Exception(f"No shared data found for call_id: {call_id}")

            # Download the recording from Vonage
            vonage_client = VonageClient(
                application_id=VONAGE_APPLICATION_ID,
                private_key=VONAGE_APPLICATION_PRIVATE_KEY_PATH,
            )
            voice = Voice(vonage_client)
            recording_bytes = voice.get_recording(recording_url)

            # Upload the recording to Supabase
            file_path = f'Cursor-Test/{call_id}.mp3'
            upload_response = supabase.storage.from_('recordings').upload(file_path, recording_bytes, {
                "Content-Type": "audio/mpeg"
            })
            if upload_response.status_code != 200:
                raise Exception(f"Failed to upload recording: {upload_response.text}")

            # Construct the Supabase URL for the uploaded file
            supabase_url = f"https://cedxguhjiaxatqwsccrp.supabase.co/storage/v1/object/public/recordings/Franko_Test/{call_id}.mp3"
            # Save the Supabase URL to the shared_data instance
            shared_data.recording_url = supabase_url
            print(f"Supabase URL for call_id {call_id}: {supabase_url}")

            print("Recording URL saved to Supabase successfully")
        except Exception as e:
            print(f"Exception occurred while saving recording URL: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        print("No recording URL found in the request data")
        raise HTTPException(status_code=400, detail="No recording URL provided")

    return {"message": "Recording processed successfully"}






# async def play_audio_file(websocket: WebSocket):
#     # audio_folder_path = r"C:\Users\fletc\Desktop\Franko - 06\SalesGPT\buffer_audio"
#     audio_folder_path = "/mnt/buffer_audio" 
#     audio_files = [f for f in os.listdir(audio_folder_path) if f.endswith('.raw')]
    
#     if not audio_files:
#         print("No audio files found in the buffer folder.")
#         return

#     try:
#         # Randomly select one of the audio files
#         selected_file = random.choice(audio_files)
#         audio_file_path = os.path.join(audio_folder_path, selected_file)
        
#         print(f"[{datetime.now()}] - Sending Audio Buffer File Begun: {selected_file}")
        
#         with open(audio_file_path, 'rb') as f:
#             audio_data = f.read()
#         await send_audio(websocket, audio_data, 0)  # Assume 3 seconds duration, adjust as needed
#         print(f"[{datetime.now()}] - Sending Audio Buffer File Returned")
#     except Exception as e:
#         print(f"Error playing audio file: {e}")


async def play_audio_file(audio_manager: AudioManager):
    audio_folder_path = "/mnt/buffer_audio" 
    audio_files = [f for f in os.listdir(audio_folder_path) if f.endswith('.raw')]
    
    if not audio_files:
        print("No audio files found in the buffer folder.")
        return 0

    try:
        selected_file = random.choice(audio_files)
        audio_file_path = os.path.join(audio_folder_path, selected_file)
        
        with open(audio_file_path, 'rb') as f:
            audio_data = f.read()
        duration = BUFFER_FILE_DURATIONS.get(selected_file, 3.0)  # Default to 3 seconds if not found
        await audio_manager.play_audio(audio_data, duration)
        return duration
    except Exception as e:
        print(f"Error playing audio file: {e}")
        return 0

BUFFER_FILE_DURATIONS = {
    "01_buffer.raw": 1.34,  # Duration in seconds
    "02_buffer.raw": 1.85,
    "03_buffer.raw": 2.22,
    "04_buffer.raw": 1.85,
    "05_buffer.raw": 2.18
}



# async def generate_and_send_speech(websocket: WebSocket, conversation_history: list, human_response: str, agent_response: str):
#     try:
#         print(f"{datetime.now()} Generate and Send Speech Begun")
        
#         results = {}
#         empathy_statement_processed = False

#         # Check if it's the first turn in the conversation
#         is_first_turn = len(conversation_history) == 0

#         # Only play the audio file if it's not the first turn
#         if not is_first_turn:
#             # Start playing the audio file asynchronously without awaiting
#             asyncio.create_task(play_audio_file(websocket))
        
#         async for partial_result in sales_api.run_chains(conversation_history, human_response, agent_response):
#             results.update(partial_result)
            
#             if "empathy_statement" in partial_result and not empathy_statement_processed:
#                 print(f"{datetime.now()} Empathy Statement Audio Generation Begun")
#                 empathy_audio_data, empathy_duration = TextToSpeech().generate_speech(results["empathy_statement"])
#                 print(f"{datetime.now()} Empathy Statement Audio Generation Returned")
                
#                 print(f"{datetime.now()} Empathy Statement Audio to Websocket Begun")
#                 await send_audio(websocket, empathy_audio_data, empathy_duration)
#                 print(f"{datetime.now()} Empathy Statement Audio to Websocket Returned")
                
#                 empathy_statement_processed = True

#         print(f"{datetime.now()} Lead Interviewer Statement Generation Begun")
#         sales_utterance_response = await sales_api.do(
#             conversation_history,
#             human_response,
#             empathy_statement=results.get("empathy_statement"),
#             key_points=results.get("key_points"),
#             current_goal_review=results.get("current_goal_review"),
#         )

#         # Extract the desired part of the response
#         extracted_response = extract_desired_response(sales_utterance_response)
#         print(f"{datetime.now()} Lead Interviewer Statement Generation Returned")

#         print(f"{datetime.now()} Lead Interviewer Audio Generation Begun")
#         sales_utterance_audio_data, sales_utterance_duration = TextToSpeech().generate_speech(extracted_response + " ...!")
#         print(f"{datetime.now()} Lead Interviewer Audio Generation Returned")

#         print(f"{datetime.now()} Lead Interviewer Audio to Websocket Begun")
#         await send_audio(websocket, sales_utterance_audio_data, sales_utterance_duration)
#         print(f"{datetime.now()} Lead Interviewer Audio to Websocket Returned")

#         print(f"{datetime.now()} Generate and Send Speech Returned")
#         return results.get("empathy_statement"), extracted_response, sales_utterance_duration

#     except Exception as e:
#         print(f"Error in generate_and_send_speech: {e}")
#         print(f"Error in generate_and_send_speech: {type(e).__name__}: {e}")
#         print(traceback.format_exc())



async def generate_and_send_speech(audio_manager: AudioManager, conversation_history: list, human_response: str, agent_response: str):
    try:
        print(f"[{datetime.now()}] Generate and Send Speech Begun")
        
        results = {}
        total_duration = 0
        
        # Check if it's the first turn in the conversation
        is_first_turn = len(conversation_history) == 0
        print(f"[{datetime.now()}] Is first turn: {is_first_turn}")

        # Only play the buffer audio if it's not the first turn
        if not is_first_turn:
            print(f"[{datetime.now()}] Playing buffer audio")
            buffer_duration = await play_audio_file(audio_manager)
            total_duration += buffer_duration
            print(f"[{datetime.now()}] Buffer audio played, duration: {buffer_duration}")

        # Use the run_chains method to get all results
        print(f"[{datetime.now()}] Starting run_chains")
        async for partial_result in sales_api.run_chains(conversation_history, human_response, agent_response):
            results.update(partial_result)
            print(f"[{datetime.now()}] Partial result received: {partial_result.keys()}")

            if "empathy_statement" in partial_result:
                empathy_statement = partial_result["empathy_statement"]
                print(f"[{datetime.now()}] Generating speech for empathy statement")
                empathy_audio_data, empathy_duration = TextToSpeech().generate_speech(empathy_statement)
                print(f"[{datetime.now()}] Empathy statement speech generated, duration: {empathy_duration}")
                
                print(f"[{datetime.now()}] Waiting for current audio to finish")
                await audio_manager.wait_for_current_audio()
                print(f"[{datetime.now()}] Playing empathy statement audio")
                await audio_manager.play_audio(empathy_audio_data, empathy_duration)
                total_duration += empathy_duration
                print(f"[{datetime.now()}] Empathy statement audio played")

        # Generate sales utterance
        print(f"[{datetime.now()}] Generating sales utterance")
        sales_utterance_response = await sales_api.do(
            conversation_history,
            human_response,
            empathy_statement=results.get("empathy_statement", ""),
            key_points=results.get("key_points", ""),
            current_goal_review=results.get("current_goal_review", "")
        )
        print(f"[{datetime.now()}] Sales utterance generated")

        extracted_response = extract_desired_response(sales_utterance_response)
        print(f"[{datetime.now()}] Generating speech for sales utterance")
        sales_utterance_audio_data, sales_utterance_duration = TextToSpeech().generate_speech(extracted_response + " ...!")
        print(f"[{datetime.now()}] Sales utterance speech generated, duration: {sales_utterance_duration}")
        
        print(f"[{datetime.now()}] Waiting for current audio to finish")
        await audio_manager.wait_for_current_audio()
        print(f"[{datetime.now()}] Playing sales utterance audio")
        await audio_manager.play_audio(sales_utterance_audio_data, sales_utterance_duration)
        total_duration += sales_utterance_duration
        print(f"[{datetime.now()}] Sales utterance audio played")

        print(f"[{datetime.now()}] Generate and Send Speech Returned. Total duration: {total_duration}")
        return results.get("empathy_statement", ""), extracted_response, total_duration

    except Exception as e:
        print(f"[{datetime.now()}] Error in generate_and_send_speech: {e}")
        print(traceback.format_exc())
        return None, None, 0



def extract_desired_response(response):
    # Find the start and end of the desired section
    start = response.find("***")
    end = response.rfind("***")
    
    if start != -1 and end != -1 and start < end:
        # Extract the content between the *** markers
        extracted = response[start+3:end].strip()
        return extracted
    else:
        # If the markers are not found, return the original response
        return response



async def send_audio(vonage_websocket: WebSocket, audio_data, duration, empathy_statement_played=None):
    # logging.debug(f"{datetime.now()}: send_audio task started")
    
    try:
        samples = bytearray(audio_data)
        # Set the buffer size to 6 chunks of 20ms audio (320 * 2 bytes per chunk)
        buffer_size = int(2 / 0.02)
        chunk_size = 320 * 2

        print(f"{datetime.now()} Sending Audio Stream - Begun")
        while len(samples) >= chunk_size * buffer_size:
            for i in range(buffer_size):
                chunk = samples[i*chunk_size:(i+1)*chunk_size]
                await vonage_websocket.send_bytes(chunk)
                # print(f"Sent audio chunk of size {len(chunk)} bytes")
            samples = samples[buffer_size*chunk_size:]
            await asyncio.sleep(0.02)
        
        # Send the remaining audio data only if it forms complete chunks of 640 bytes
        while len(samples) >= chunk_size:
            chunk = samples[:chunk_size]
            await vonage_websocket.send_bytes(chunk)
            # print(f"Sent remaining audio chunk of size {len(chunk)} bytes")
            samples = samples[chunk_size:]
            await asyncio.sleep(0.02)
        
        # If there are any remaining bytes that don't form a complete chunk, send an empty chunk
        if len(samples) > 0:
            await vonage_websocket.send_bytes(bytearray())
            print(f"{datetime.now()} Sending Audio Stream - Finished")



        # # Wait for the duration of the audio
        # await asyncio.sleep(duration)
        
        # Set the event to indicate that the empathy statement has been played
        if empathy_statement_played:
            empathy_statement_played.set()
            print(f"{datetime.now()}: Empathy statement playback completed")
            # logging.debug(f"Empathy statement playback completed")
        
        
        # logging.debug(f"{datetime.now()}: send_audio task completed")
    
    except Exception as e:
        logging.error(f"Error in send_audio: {e}")
        logging.error(f"Error in send_audio: {type(e).__name__}: {e}")
        logging.error(traceback.format_exc())







class WebSocketManager:
    def __init__(self, websocket: WebSocket, shared_data: SharedData):
        self.websocket = websocket
        self.shared_data = shared_data
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 1  # Initial delay in seconds
        self.is_reconnecting = False

    async def connect(self):
        await self.websocket.accept()
        self.shared_data.set_websocket(self.websocket)
        self.shared_data.websocket_ready.set()  # Set the websocket_ready event
        print("WebSocket connected.")

    async def disconnect(self):
        await self.websocket.close()
        print("WebSocket disconnected.")

    async def send_message(self, message: dict):
        await self.websocket.send_json(message)

    async def receive_message(self):
        try:
            message = await self.websocket.receive()
            if message["type"] == "websocket.receive":
                return message
            elif message["type"] == "websocket.disconnect":
                raise WebSocketDisconnect(message["code"], message["reason"])
            else:
                raise ValueError(f"Unexpected message type: {message['type']}")
        except WebSocketDisconnect as e:
            print(f"WebSocket disconnected: code={e.code}, reason={e.reason}")
            raise

    async def reconnect(self):
        if self.is_reconnecting:
            return

        self.is_reconnecting = True
        self.reconnect_attempts = 0

        while self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                self.reconnect_attempts += 1
                print(f"Attempting to reconnect WebSocket (Attempt {self.reconnect_attempts})...")

                # Create a new WebSocket connection with the same URI
                new_websocket = await WebSocket.connect(self.websocket.url)

                # Update the shared data with the new WebSocket connection
                self.shared_data.set_websocket(new_websocket)

                # Update the WebSocketManager instance with the new WebSocket connection
                self.websocket = new_websocket

                print("WebSocket reconnected successfully.")
                self.is_reconnecting = False
                return

            except Exception as e:
                print(f"Failed to reconnect WebSocket: {e}")
                # Implement exponential backoff for retry delay
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay *= 2  # Double the delay for the next attempt

        print("Max reconnect attempts reached. WebSocket reconnection failed.")
        self.is_reconnecting = False

    async def should_reconnect(self):
        # Check if the call is still active in the shared data
        return not self.shared_data.call_completed





# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket, call_id: str = Query(...)):
#     print(f"WebSocket connection opened for call_id: {call_id}")
#     shared_data = shared_data_dict[call_id]
#     websocket_manager = WebSocketManager(websocket, shared_data)
#     await websocket_manager.connect()

#     try:
#         # Initialize Deepgram client
#         config = DeepgramClientOptions(options={"keepalive": "true"})
#         deepgram: DeepgramClient = DeepgramClient(os.environ["DEEPGRAM_API_KEY"], config)
#         dg_connection = deepgram.listen.asynclive.v("1")


#         async def on_message(self, result, **kwargs):
#             if result.channel.alternatives[0].words:
#                 shared_data.update_word_timestamp()
#             else:
#                 shared_data.update_no_word_timestamp()
#             handle_transcription(result, shared_data)


#         # Define the error event handler
#         async def on_error(self, error, **kwargs):
#             print(f"Error: {error}")

#         # Register the event handlers
#         dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
#         dg_connection.on(LiveTranscriptionEvents.Error, on_error)

#         # Set the transcription options
#         options = LiveOptions(
#             model="nova-2",
#             filler_words=True,
#             language="en-US",
#             punctuate=True,
#             encoding="linear16",
#             channels=1,
#             sample_rate=16000,
#             interim_results=True,
#         )

#         # Start the Deepgram connection
#         await dg_connection.start(options)

#         while True:
#             try:
#                 message = await websocket_manager.receive_message()
#                 # logger.debug(f"Received WebSocket message: {message}")
#                 if message["type"] == "websocket.receive":
#                     if "text" in message:
#                         # Handle JSON data
#                         data = json.loads(message["text"])
#                         # Process the JSON data as needed
#                     elif "bytes" in message:
#                         # Handle binary data
#                         audio_data = message["bytes"]
#                         await dg_connection.send(audio_data)
                        
#             except WebSocketDisconnect as e:
#                 logger.error(f"WebSocket disconnected: code={e.code}")
#                 if hasattr(e, 'reason'):
#                     logger.error(f"Disconnection reason: {e.reason}")
#                 else:
#                     logger.error("Disconnection reason not provided")

#                 print(f"WebSocket disconnected: code={e.code}, reason={e.reason}")
#                 if await websocket_manager.should_reconnect():
#                     print("Attempting to reconnect...")
#                     await reconnect_deepgram(dg_connection, shared_data, websocket)
#                     if not shared_data.is_reconnecting:
#                         continue  # If reconnection was successful, continue with the next iteration
#                     else:
#                         print("Call terminated. WebSocket will not reconnect.")
#                         break


#     except Exception as e:
#         print(f"Error in WebSocket endpoint: {e}")
#         print(traceback.format_exc())

#     finally:
#         # Close the Deepgram connection
#         await dg_connection.finish()

#         try:
#             if websocket_manager.websocket.client_state.name != "DISCONNECTED":
#                 # Close the WebSocket connection if it's not already closed
#                 await websocket_manager.disconnect()
#         except Exception as e:
#             print(f"Error closing WebSocket connection: {e}")
#             print(traceback.format_exc())





@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, call_id: str = Query(...)):
    print(f"WebSocket connection opened for call_id: {call_id}")
    shared_data = shared_data_dict[call_id]
    websocket_manager = WebSocketManager(websocket, shared_data)
    await websocket_manager.connect()

    deepgram = DeepgramClient(os.environ["DEEPGRAM_API_KEY"])
    dg_connection = deepgram.listen.live.v("1")

    def on_open(self, open, **kwargs):
        print(f"Deepgram connection opened: {open}")

    def on_message(self, result, **kwargs):
        print(f"{datetime.now()} Deepgram transcription received:")
        # pprint(result)
        
        if result.channel.alternatives[0].words:
            shared_data.update_word_timestamp()
        else:
            shared_data.update_no_word_timestamp()
        
        handle_transcription(result, shared_data)

    def on_error(self, error, **kwargs):
        print(f"Deepgram Error: {error}")

    def on_close(self, close, **kwargs):
        print(f"Deepgram connection closed: {close}")

    dg_connection.on(LiveTranscriptionEvents.Open, on_open)
    dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
    dg_connection.on(LiveTranscriptionEvents.Error, on_error)
    dg_connection.on(LiveTranscriptionEvents.Close, on_close)

    options = LiveOptions(
        model="nova-2",
        punctuate=True,
        language="en-US",
        encoding="linear16",
        channels=1,
        sample_rate=16000,
        interim_results=True,
    )

    try:
        dg_connection.start(options)
        print("Deepgram connection started successfully")

        while True:
            try:
                message = await websocket_manager.receive_message()
                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        audio_data = message["bytes"]
                        dg_connection.send(audio_data)
                    
            except WebSocketDisconnect as e:
                logger.error(f"WebSocket disconnected: code={e.code}")
                logger.error(f"Disconnection reason: {getattr(e, 'reason', 'Unknown')}")
                print(f"WebSocket disconnected: code={e.code}, reason={getattr(e, 'reason', 'Unknown')}")
                
                if await websocket_manager.should_reconnect():
                    print("Attempting to reconnect...")
                    dg_connection = deepgram.listen.live.v("1")
                    dg_connection.on(LiveTranscriptionEvents.Open, on_open)
                    dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
                    dg_connection.on(LiveTranscriptionEvents.Error, on_error)
                    dg_connection.on(LiveTranscriptionEvents.Close, on_close)
                    dg_connection.start(options)
                    print("Deepgram connection restarted successfully")
                    continue
                else:
                    print("Call terminated. WebSocket will not reconnect.")
                    break

    except Exception as e:
        print(f"Error in WebSocket endpoint: {e}")
        print(traceback.format_exc())

    finally:
        if dg_connection:
            dg_connection.finish()
            print("Deepgram connection closed")

        try:
            if websocket_manager.websocket.client_state.name != "DISCONNECTED":
                await websocket_manager.disconnect()
                print("WebSocket disconnected successfully")
        except Exception as e:
            print(f"Error closing WebSocket connection: {e}")
            print(traceback.format_exc())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)