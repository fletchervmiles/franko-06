from fastapi import FastAPI, HTTPException, Query, Body, WebSocket, Request, WebSocketDisconnect
from starlette.websockets import WebSocketState
from websockets.exceptions import ConnectionClosedError, WebSocketException, ConnectionClosed
import vonage
from vonage import Client as VonageClient, Voice
import os
import io
import wave
import struct
from dotenv import load_dotenv
from uuid import uuid4
from pydantic import BaseModel, Field
import asyncio
# from salesgpt.logger import time_logger, logger
from salesgpt.salesgptapi02 import SalesGPTAPI
import redis
import json
from pprint import pprint
from enum import Enum
import re
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
import websockets
import base64
import aiohttp
from collections import deque
# from deepgram import (
#     DeepgramClient,
#     DeepgramClientOptions,
#     LiveTranscriptionEvents,
#     LiveOptions,
# )

from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
    DeepgramClientOptions,
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

# AssemblyAI endpoint URL
URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"

# Retrieve the AssemblyAI API key from environment variables
auth_key = os.environ.get("ASSEMBLYAI_API_KEY")

# Create an instance of SalesGPTAPI
# # the SalesGPTAPI class is initialised once when the server starts with the config path getting passed in.
# sales_api = SalesGPTAPI(config_path=CONFIG_PATH, verbose=False)

# Load environment variables
load_dotenv()
tracemalloc.start()

call_instances = {}

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

# # Initialize Vonage client
# vonage_client = VonageClient(
#     application_id=VONAGE_APPLICATION_ID,
#     private_key=VONAGE_APPLICATION_PRIVATE_KEY_PATH,
# )
# voice = Voice(vonage_client)


class CallRequest(BaseModel):
    client_name: str
    interviewee_name: str 
    interviewee_last_name: str
    interviewee_email: str
    to_number: str


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


class AudioQueue:
    def __init__(self):
        self.queue = deque()
        self.lock = asyncio.Lock()

    async def enqueue(self, audio_data):
        async with self.lock:
            self.queue.append(audio_data)

    async def dequeue(self):
        async with self.lock:
            return self.queue.popleft() if self.queue else None

    async def is_empty(self):
        async with self.lock:
            return len(self.queue) == 0

    async def clear(self):
        async with self.lock:
            self.queue.clear()


class SharedData:
    def __init__(self):
        self._data = {}
        self.websocket = None
        self.websocket_ready = asyncio.Event()
        self.call_completed = False
        self.state_machine = None
        self.is_reconnecting = False
        self.reconnection_attempts = 0
        self.call_id = None  # Add this line
        
        # These are for the listening functionality
        self.transcript_parts = []
        self.last_word_time = None
        self.last_no_word_time = None

        # New
        self.audio_queue = AudioQueue()  # New audio queue




    def set_websocket(self, websocket):
        self.websocket = websocket

    def get_websocket(self):
        return self.websocket
    
    def set_call_id(self, call_id):  # Add this method
        self.call_id = call_id

    def set_state_machine(self, state_machine):
        self.state_machine = state_machine
        # print("State machine set.")

    # These four methods are for the listening functionality
    def add_part(self, part):
        if self.state_machine and self.state_machine.get_current_state() == CallState.LISTEN_FOR_USER_RESPONSE:
            self.transcript_parts.append(part)

    def get_full_transcript(self):
        if self.state_machine and self.state_machine.get_current_state() == CallState.LISTEN_FOR_USER_RESPONSE:
            return ' '.join(self.transcript_parts)
        return ''

    def update_word_timestamp(self):
        if self.state_machine and self.state_machine.get_current_state() == CallState.LISTEN_FOR_USER_RESPONSE:
            self.last_word_time = datetime.now()
            # print(f"[{self.last_word_time}] Word timestamp updated")

    def update_no_word_timestamp(self):
        if self.state_machine and self.state_machine.get_current_state() == CallState.LISTEN_FOR_USER_RESPONSE:
            self.last_no_word_time = datetime.now()
            # print(f"[{self.last_no_word_time}] No word timestamp updated")


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



class StateMachine:
    def __init__(self, call_id, r, shared_data, sales_api):
        self.call_id = call_id
        self.r = r
        # self.vonage_client = vonage_client
        self.shared_data = shared_data
        self.sales_api = sales_api
        self.set_state(CallState.CALL_SETUP)
        self.event_queue = asyncio.Queue()
        self.human_response_received = asyncio.Event()
        self.shared_data.set_state_machine(self)
        self.shared_data.set_call_id(call_id)  # Add this line
        self.cleanup_task = None

        # Get the interviewee name from the sales_api config
        self.interviewee_name = self.sales_api.config.get('interviewee_name', 'Interviewee')

    def get_current_state(self):
        return self.state

    def set_state(self, state):
        self.state = state
        self.shared_data.set_state_machine(self)

    async def call_setup(self):
        print(f"Setting up the call for call_id: {self.call_id}")
        # print("Setting up the call...")

        # Wait until the call is answered
        while r.get(f'{self.call_id}_call_answered').decode("utf-8") == 'False':
            await asyncio.sleep(0.1)

        await self.shared_data.websocket_ready.wait()
        # print(f"WebSocket in call_setup: {self.shared_data.get_websocket()}")
        # print("WebSocket Open")

        await self.event_queue.put(CallState.GENERATE_FRANKO_RESPONSE)


    async def cleanup(self):
        # Cancel any ongoing tasks
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        # Clear the event queue
        while not self.event_queue.empty():
            await self.event_queue.get()
        
        # Cancel any ongoing operations
        # For example, if you have any ongoing API calls or database operations:
        if hasattr(self, 'current_operation'):
            self.current_operation.cancel()
        
        # Reset any state variables
        self.state = CallState.CALL_SETUP
        
        print(f"{datetime.now()}: StateMachine cleaned up for call_id: {self.call_id}")



    async def generate_franko_response(self):
        try:
            print(f"{datetime.now()} Generate Franko Response Begun")


            # Get conversation history and human response from Redis
            conversation_history = json.loads(self.r.get(f"{self.call_id}_conversation_history").decode("utf-8"))
            human_response = self.r.get(f'{self.call_id}_human_response')
            human_response = human_response.decode("utf-8") if human_response else "N/A"
            agent_response = self.r.get(f'{self.call_id}_agent_response')
            agent_response = agent_response.decode("utf-8") if agent_response else "N/A"

            # Pass the websocket object and conversation data to the generate_and_send_speech function
            empathy_statement, extracted_response, audio_state_delay = await generate_and_send_speech(
                self.shared_data.get_websocket(), 
                self.call_id,  # Add this line to pass the call_id
                conversation_history, 
                human_response, 
                agent_response,
                self.shared_data  # Add this line to pass shared_data
            )

            # Get the current timestamp in minutes since the start of the call
            current_time = time.time()
            interview_start_time = self.sales_api.sales_agent.interview_start_time
            timestamp = f"[{((current_time - interview_start_time) / 60):.2f}]"
            
            agent_name = "Franko"
            ai_message = f"{empathy_statement} {extracted_response}"

            # Print the full AI message with breaks
            print(f"\nFull AI Message:\n{ai_message}\n")

            clean_ai_message = strip_break_tags(ai_message)

            # Add timestamp to the agent's response
            timestamped_ai_message = f"{timestamp} {agent_name}: {clean_ai_message}"

            # Print the cleaned AI message
            print(f"\nCleaned AI Message:\n{clean_ai_message}\n")

            self.r.set(f'{self.call_id}_agent_response', clean_ai_message)
            conversation_history.append(timestamped_ai_message)
            self.r.set(f'{self.call_id}_conversation_history', json.dumps(conversation_history))

            # Update the short conversation history (without timestamp)
            self.sales_api.sales_agent.update_short_conversation_history(agent_name, clean_ai_message)

            # Run the update_conversation_stage method as a separate task
            print(f"{datetime.now()} Update Conversation Stage (same as determine but in test14 file) Begun")
            asyncio.create_task(self.update_conversation_stage())

            # Sleep for the audio_state_delay time
            print(f"Sleeping for audio_state_delay: {audio_state_delay:.2f} seconds")
            print(f"{datetime.now()} Audio state delay starting...")
            await asyncio.sleep(max(audio_state_delay, 0))
            print(f"{datetime.now()} Audio state delay ended!")


            print(f"{datetime.now()} Generate Franko Response Returned")
            # Transition to the LISTEN_FOR_USER_RESPONSE state
            await self.event_queue.put(CallState.LISTEN_FOR_USER_RESPONSE)

        except Exception as e:
            logger.exception("An error occurred in generate_franko_response: %s", str(e))
            # Handle the error gracefully, e.g., send an error message to the user or retry the operation


    async def update_conversation_stage(self):
        await self.sales_api.update_conversation_stage()


    async def listen_for_user_response(self):
        print(f"{datetime.now()} Listen for User Response Begun for call_id: {self.call_id}")

        # This resets the transcripts before checking again
        self.shared_data.reset_transcripts()
    
        # Get the current timestamp in minutes since the start of the call
        current_time = time.time()
        interview_start_time = self.sales_api.sales_agent.interview_start_time
        timestamp = f"[{((current_time - interview_start_time) / 60):.2f}]"

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

        # Use the interviewee_name from the instance variable
        interviewee_name = self.interviewee_name

        human_input = f"{timestamp} {interviewee_name}: " + full_transcript.strip()
        # print(f"[{datetime.now()}] Appended Human Input: {human_input}")

        conversation_history = json.loads(self.r.get(f'{self.call_id}_conversation_history').decode("utf-8"))
        conversation_history.append(human_input)
        self.r.set(f'{self.call_id}_conversation_history', json.dumps(conversation_history))
        # print(f"Updated Conversation History: {conversation_history}")
        
        # Update the short conversation history (without timestamp)
        self.sales_api.sales_agent.update_short_conversation_history(self.interviewee_name, full_transcript.strip())


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
        if time_diff > timedelta(seconds=2.5):
            return True
            print(f"{datetime.now()}: - Interviewee Response Time Checker Loop Condition Met")
    return False


def handle_transcription(result, shared_data):
    sentence = result.channel.alternatives[0].transcript
    call_id = shared_data.call_id  # Add this line

    if result.is_final and result.channel.alternatives[0].words:
        shared_data.add_part(sentence)
        print(f"{datetime.now()}: Appending partial transcript - {sentence}")


def strip_break_tags(text):
    return re.sub(r'<break\s+time="[^"]*"\s*/>', '', text)



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

    # def generate_speech(self, text):
    #     start_time = time.time()
    #     ELEVENLABS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{self.VOICE_ID}?optimize_streaming_latency=3&output_format=pcm_16000"
    #     headers = {
    #         "xi-api-key": self.ELEVENLABS_API_KEY,
    #         "Content-Type": "application/json"
    #     }
    #     payload = {
    #         "model_id": "eleven_turbo_v2_5",
    #         # "model_id": "eleven_multilingual_v2",
    #         # "model_id": "eleven_monolingual_v1",
    #         "text": text,
    #         "voice_settings": {
    #             "similarity_boost": 0.5,
    #             "stability": 0.5
    #         }
    #     }
    #     try:
    #         response = requests.post(ELEVENLABS_URL, headers=headers, json=payload, timeout=10)  # Added timeout
    #         response.raise_for_status()  # This will raise an exception for HTTP error codes
    #         print(f"Time taken for ElevenLabs API request: {time.time() - start_time} seconds")
    #         return response.content, 0  # Assuming a fixed duration for simplicity
    #     except requests.exceptions.HTTPError as e:
    #         logging.error(f"HTTPError during ElevenLabs API request: {e.response.status_code} {e.response.text}")
    #     except requests.exceptions.RequestException as e:
    #         logging.error(f"Error during ElevenLabs API request: {e}")
    #     print(f"Failed to generate speech for text: {text}")
    #     return None, 0  # Indicate failure


    # def generate_speech(self, text):
    #     start_time = time.time()
    #     ELEVENLABS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{self.VOICE_ID}?optimize_streaming_latency=3&output_format=pcm_16000"
    #     headers = {
    #         "xi-api-key": self.ELEVENLABS_API_KEY,
    #         "Content-Type": "application/json"
    #     }
    #     payload = {
    #         "model_id": "eleven_turbo_v2_5",
    #         "text": text,
    #         "voice_settings": {
    #             "similarity_boost": 1,
    #             "stability": 1
    #         }
    #     }
    #     try:
    #         response = requests.post(ELEVENLABS_URL, headers=headers, json=payload, timeout=10)
    #         response.raise_for_status()
    #         print(f"Time taken for ElevenLabs API request: {time.time() - start_time} seconds")
            
    #         audio_content = response.content
    #         duration = self.calculate_audio_duration(audio_content)
            
    #         return audio_content, duration
    #     except requests.exceptions.HTTPError as e:
    #         logging.error(f"HTTPError during ElevenLabs API request: {e.response.status_code} {e.response.text}")
    #     except requests.exceptions.RequestException as e:
    #         logging.error(f"Error during ElevenLabs API request: {e}")
    #     print(f"Failed to generate speech for text: {text}")
    #     return None, 0


    async def generate_speech(self, text):
        start_time = time.time()
        ELEVENLABS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{self.VOICE_ID}?optimize_streaming_latency=3&output_format=pcm_16000"
        headers = {
            "xi-api-key": self.ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "model_id": "eleven_turbo_v2_5",
            "text": text,
            "voice_settings": {
                "similarity_boost": 1,
                "stability": 1
            }
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(ELEVENLABS_URL, headers=headers, json=payload, timeout=10) as response:
                    if response.status == 200:
                        audio_content = await response.read()
                        duration = self.calculate_audio_duration(audio_content)
                        return audio_content, duration
                    else:
                        error_content = await response.text()
                        print(f"{datetime.now()} - ElevenLabs API error: Status {response.status}")
                        print(f"{datetime.now()} - Error content: {error_content}")
                        try:
                            error_json = json.loads(error_content)
                            print(f"{datetime.now()} - Error details: {json.dumps(error_json, indent=2)}")
                        except json.JSONDecodeError:
                            print(f"{datetime.now()} - Could not parse error content as JSON")
                        return None, 0
        except aiohttp.ClientError as e:
            print(f"{datetime.now()} - Network error during ElevenLabs API request: {str(e)}")
        except Exception as e:
            print(f"{datetime.now()} - Unexpected error during ElevenLabs API request: {str(e)}")
            print(f"{datetime.now()} - Error type: {type(e).__name__}")
            print(f"{datetime.now()} - Error details:\n{traceback.format_exc()}")
        return None, 0

    def calculate_audio_duration(self, audio_content):
        # PCM 16-bit audio at 16000 Hz
        sample_width = 2  # 16-bit = 2 bytes
        sample_rate = 16000
        
        # Calculate number of samples
        num_samples = len(audio_content) // sample_width
        print(f"Number of samples: {num_samples}")  # Debugging output

        # Calculate duration in seconds
        duration = num_samples / sample_rate
        print(f"Duration in seconds: {duration}")  # Debugging output
        
        return duration


@app.post("/call")
async def make_outgoing_call(call_request: CallRequest):
    try:
        call_id = str(uuid4())
        print(f"{datetime.now()}: Call initiated with call_id: {call_id}")

        # Create a dynamic configuration
        dynamic_config = {
            "client_name": call_request.client_name,
            "interviewee_name": call_request.interviewee_name,
            "interviewee_last_name": call_request.interviewee_last_name,
            "interviewee_email": call_request.interviewee_email,
            "to_number": call_request.to_number,
        }

        # # Save the dynamic configuration to a temporary JSON file
        # temp_config_path = f"temp_config_{call_id}.json"
        # with open(temp_config_path, 'w') as f:
        #     json.dump(dynamic_config, f)

        # Store call-related data in Redis
        r.set(f'{call_id}_call_answered', 'False')
        r.set(f'{call_id}_human_response', "")
        r.set(f'{call_id}_agent_response', "")
        r.set(f'{call_id}_conversation_history', json.dumps([]))


        sales_gpt_api = SalesGPTAPI(config=dynamic_config, call_id=call_id)

        # # Create new instances for this call
        # sales_gpt_api = SalesGPTAPI(config_path=temp_config_path, call_id=call_id)
        sales_gpt = sales_gpt_api.initialize_agent()
        shared_data = SharedData()
        # state_machine = StateMachine(call_id=call_id, r=r, vonage_client=vonage_client, shared_data=shared_data, sales_api=sales_gpt_api)
        state_machine = StateMachine(call_id=call_id, r=r, shared_data=shared_data, sales_api=sales_gpt_api)


        # Store instances in the dictionary
        call_instances[call_id] = {
            "sales_gpt_api": sales_gpt_api,
            "sales_gpt": sales_gpt,
            "shared_data": shared_data,
            "state_machine": state_machine
        }

        # Start the state machine asynchronously
        asyncio.create_task(state_machine.start())

        print(f"Vonage Application ID: {VONAGE_APPLICATION_ID}")
        print(f"Vonage Private Key Path: {VONAGE_APPLICATION_PRIVATE_KEY_PATH}")
        
        # Check if the private key file exists and is readable
        if not os.path.isfile(VONAGE_APPLICATION_PRIVATE_KEY_PATH):
            raise FileNotFoundError(f"Vonage private key file not found: {VONAGE_APPLICATION_PRIVATE_KEY_PATH}")
        
        if not os.access(VONAGE_APPLICATION_PRIVATE_KEY_PATH, os.R_OK):
            raise PermissionError(f"Cannot read Vonage private key file: {VONAGE_APPLICATION_PRIVATE_KEY_PATH}")

        # Initialize Vonage client inside the function
        vonage_client = VonageClient(
            application_id=VONAGE_APPLICATION_ID,
            private_key=VONAGE_APPLICATION_PRIVATE_KEY_PATH,
        )
        voice = Voice(vonage_client)

        # PROD CHANGE
        # franko-06.onrender.com
        response = vonage_client.voice.create_call({
            'to': [{'type': 'phone', 'number': call_request.to_number}], # Use to_number from the request
            'from': {'type': 'phone', 'number': VONAGE_NUMBER},
            'ncco': [
                {
                    'action': 'record',
                    'eventUrl': [f'https://franko-06.onrender.com/vonage_recording?call_id={call_id}'],
                    'format': 'mp3'
                },
                {
                    'action': 'connect',
                    'endpoint': [
                        {
                            'type': 'websocket',
                            'uri': f'wss://franko-06.onrender.com/ws?call_id={call_id}',
                            'content-type': 'audio/l16;rate=16000',
                            'headers': {
                                'language': 'en-GB',
                                'caller-id': VONAGE_NUMBER
                            }
                        }
                    ]
                }
            ],
            'event_url': [f'https://franko-06.onrender.com/vonage_call_status?call_id={call_id}'],
            'event_method': 'POST'
        })

        # # Clean up the temporary config file
        # os.remove(temp_config_path)

        return {"message": "Call initiated", "call_id": call_id}

    except vonage.errors.AuthenticationError as e:
        print(f"Vonage Authentication Error: {str(e)}")
        raise HTTPException(status_code=401, detail="Vonage authentication failed")

    except Exception as e:
        print(f"Error in make_outgoing_call: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=str(e))



@app.post("/vonage_call_status")
async def handle_vonage_call_status(call_id: str = Query(...), call_status: CallStatus = Body(...)):
    try:
        print(f"Received status: {call_status.status}, call_id: {call_id}")
        print(f"Call details: conversation_uuid: {call_status.conversation_uuid}, timestamp: {call_status.timestamp}")
        
        if call_status.status == 'answered':
            r.set(f'{call_id}_call_answered', 'True')
            print(f"{datetime.now()}: Call answered status changed to True for call_id: {call_id}")

            # Set the interview start time when the call is answered
            if call_id in call_instances:
                sales_gpt_api = call_instances[call_id]["sales_gpt_api"]
                sales_gpt_api.set_interview_start_time()
                print(f"{datetime.now()}: Interview start time set for call_id: {call_id}")
        
        elif call_status.status == 'completed':
            if call_id in call_instances:
                try:
                    print(f"{datetime.now()}: Starting termination for call_id: {call_id}")

                    # Get instances from call_instances
                    state_machine = call_instances[call_id]["state_machine"]
                    shared_data = call_instances[call_id]["shared_data"]
                    state_machine = call_instances[call_id]["state_machine"]

                    # Set the call_completed flag to True
                    shared_data.call_completed = True

                    # Print conversation history before deleting
                    conversation_history = r.get(f'{call_id}_conversation_history')
                    if conversation_history:
                        print(f"Conversation history for call_id {call_id}:")
                        print(json.loads(conversation_history.decode('utf-8')))
                    else:
                        print(f"No conversation history found for call_id {call_id}")

                    # Delay the execution by 2 seconds
                    await asyncio.sleep(60)

                    # Clean up the SharedData instance
                    shared_data.reset()
                    print(f"{datetime.now()}: SharedData instance reset for call_id: {call_id}")

                    # Clean up the state machine
                    await state_machine.cleanup()
                    print(f"{datetime.now()}: State Machine Cancelled call_id: {call_id}")

                    # Remove the instances from the global dictionary
                    del call_instances[call_id]
                    print(f"{datetime.now()}: Instances removed from call_instances for call_id: {call_id}")

                    # Delete data from Redis
                    r.delete(f'{call_id}_call_answered')
                    r.delete(f'{call_id}_human_response')
                    r.delete(f'{call_id}_agent_response')
                    r.delete(f'{call_id}_conversation_history')
                    print(f"{datetime.now()}: Redis history deleted for call_id: {call_id}")

                    print(f"Call terminated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} for call_id: {call_id}")

                except Exception as e:
                    print(f"{datetime.now()}: Error during call termination for call_id: {call_id}: {e}")
                    print(traceback.format_exc())
            else:
                print(f"{datetime.now()}: Call instances not found for call_id: {call_id}")
        
        else:
            print(f"{datetime.now()}: Unhandled call status: {call_status.status} for call_id: {call_id}")
        
    except Exception as e:
        print(f"{datetime.now()}: Error in handle_vonage_call_status for call_id: {call_id}: {e}")
        print(traceback.format_exc())
    
    return {"message": "Status update received"}





async def save_interview_data(supabase: SupabaseClient, interview_data: dict):
    try:
        response = supabase.table('user_interviews').insert(interview_data).execute()
        if response.data:
            print(f"Interview data saved successfully for call_id: {interview_data['call_id']}")
        else:
            print(f"Failed to save interview data for call_id: {interview_data['call_id']}")
    except Exception as e:
        print(f"Error saving interview data to Supabase: {e}")
        raise


@app.post("/vonage_recording")
async def handle_recording(request: Request, call_id: str = Query(...)):
    data = await request.json()
    recording_url = data.get('recording_url')

    if recording_url:
        try:
            if call_id not in call_instances:
                raise Exception(f"No call instance found for call_id: {call_id}")

            shared_data = call_instances[call_id]["shared_data"]
            sales_gpt_api = call_instances[call_id]["sales_gpt_api"]

            # Retrieve additional data
            dynamic_config = sales_gpt_api.config
            interviewee_name = dynamic_config.get('interviewee_name', '')
            interviewee_last_name = dynamic_config.get('interviewee_last_name', '')
            interviewee_email = dynamic_config.get('interviewee_email', '')
            to_number = dynamic_config.get('to_number', '')
            client_name = dynamic_config.get('client_name', 'Default')

            # Get conversation history from Redis
            conversation_history_str = r.get(f'{call_id}_conversation_history')
            if conversation_history_str:
                conversation_history = json.loads(conversation_history_str.decode("utf-8"))
            else:
                conversation_history = []

            print(f"Raw conversation history for call_id {call_id}: {conversation_history}")

            
            # Calculate overall elapsed time
            interview_start_time = sales_gpt_api.sales_agent.interview_start_time
            if interview_start_time is None:
                print(f"Warning: interview_start_time is None for call_id {call_id}")
                interview_start_time = time.time()
                overall_elapsed_time = 0
            else:
                overall_elapsed_time = time.time() - interview_start_time

            # Download the recording from Vonage
            vonage_client = VonageClient(
                application_id=VONAGE_APPLICATION_ID,
                private_key=VONAGE_APPLICATION_PRIVATE_KEY_PATH,
            )
            voice = Voice(vonage_client)

            recording_bytes = voice.get_recording(recording_url)

            # Upload the recording to Supabase
            file_path = f'{client_name}/{call_id}.mp3'
            upload_response = supabase.storage.from_('recordings').upload(file_path, recording_bytes, {
                "Content-Type": "audio/mpeg"
            })
            if upload_response.status_code != 200:
                raise Exception(f"Failed to upload recording for call_id {call_id}: {upload_response.text}")

            # Construct the Supabase URL for the uploaded file
            supabase_url = f"https://cedxguhjiaxatqwsccrp.supabase.co/storage/v1/object/public/recordings/{file_path}"
            
            # Save the Supabase URL to the shared_data instance
            shared_data.recording_url = supabase_url
            print(f"Supabase URL for call_id {call_id}: {supabase_url}")

            # Prepare interview data
            interview_data = {
                "call_id": call_id,
                "interviewee_name": interviewee_name,
                "interviewee_last_name": interviewee_last_name,
                "interviewee_email": interviewee_email,
                "to_number": to_number,
                "client_name": client_name,
                "current_date": datetime.now().isoformat(),
                "interview_start_time": datetime.fromtimestamp(interview_start_time).isoformat(),
                "overall_elapsed_time": overall_elapsed_time,
                "conversation_history": json.dumps(conversation_history),
                "audio_file_link": supabase_url
            }

            # Save interview data to Supabase
            await save_interview_data(supabase, interview_data)

            print(f"Recording URL and interview data saved to Supabase successfully for call_id {call_id}")
        except Exception as e:
            print(f"Exception occurred while processing recording for call_id {call_id}: {e}")
            print(traceback.format_exc())
            raise HTTPException(status_code=500, detail=str(e))
    else:
        print(f"No recording URL found in the request data for call_id {call_id}")
        raise HTTPException(status_code=400, detail="No recording URL provided")

    return {"message": f"Recording processed successfully for call_id {call_id}"}








# # PROD CHANGE
async def play_audio_file(websocket: WebSocket, call_id: str, shared_data: SharedData):
    # Specify the exact file path
    audio_folder_path = "/mnt/buffer_audio"
    audio_file_name = "understood_okay_audio.raw"
    audio_file_path = os.path.join(audio_folder_path, audio_file_name)

# LOCAL
# async def play_audio_file(websocket: WebSocket, call_id: str, shared_data: SharedData):
#     audio_file_name = "understood_okay_audio.raw"
#     audio_folder_path = r"C:\Users\fletc\Desktop\Franko - 06\SalesGPT\buffer_audio"  # Update this path
#     audio_file_path = os.path.join(audio_folder_path, audio_file_name)
    
    try:
        print(f"[{datetime.now()}] - Queueing Audio Buffer File Begun for call_id {call_id}: {audio_file_path}")
        
        with open(audio_file_path, 'rb') as f:
            audio_data = f.read()
        await send_audio(websocket, audio_data, 0, call_id, shared_data)
        print(f"[{datetime.now()}] - Queueing Audio Buffer File Returned for call_id {call_id}")
    except FileNotFoundError:
        print(f"Error: Audio file not found at {audio_file_path} for call_id {call_id}")
    except Exception as e:
        print(f"Error playing audio file for call_id {call_id}: {e}")

        



# async def generate_and_send_speech(websocket: WebSocket, call_id: str, conversation_history: list, human_response: str, agent_response: str):
#     try:
#         start_time = time.time()
#         print(f"{datetime.now()} Generate and Send Speech Begun for call_id: {call_id}")
        
#         results = {}
#         empathy_statement_processed = False
#         tts = TextToSpeech()  # Create a single instance of TextToSpeech

#         # Check if it's the first turn in the conversation
#         is_first_turn = len(conversation_history) == 0

#         play_audio_file_duration = 5.2 if not is_first_turn else 0  # seconds
#         empathy_duration = 0
#         sales_utterance_duration = 0

#         # Only play the audio file if it's not the first turn
#         if not is_first_turn:
#             # Start playing the audio file asynchronously without awaiting
#             asyncio.create_task(play_audio_file(websocket, call_id))
#         else:
#             play_audio_file_duration = 0  # Don't count this if it's the first turn
        
#         sales_gpt_api = call_instances[call_id]["sales_gpt_api"]
        
#         async for partial_result in sales_gpt_api.run_chains(conversation_history, human_response, agent_response):
#             results.update(partial_result)
            
#             # Skip empathy statement generation on the first turn
#             if not is_first_turn and "empathy_statement" in partial_result and not empathy_statement_processed:
#                 print(f"{datetime.now()} Empathy Statement Audio Generation Begun for call_id: {call_id}")
                
#                 empathy_audio_data, empathy_duration = await tts.generate_speech(results["empathy_statement"])
#                 print(f"{datetime.now()} Empathy Statement Audio Generation Returned for call_id: {call_id}")
                
#                 await send_audio(websocket, empathy_audio_data, empathy_duration, call_id)
#                 print(f"{datetime.now()} Empathy Statement Audio Sent for call_id: {call_id}")
                
#                 empathy_statement_processed = True

#         # Generate sales utterance audio
#         print(f"{datetime.now()} Lead Interviewer Statement Generation Begun for call_id: {call_id}")
#         sales_utterance_response = await sales_gpt_api.do(
#             conversation_history,
#             human_response,
#             empathy_statement=results.get("empathy_statement", ""),  # Use empty string if no empathy statement
#             current_goal_review=results["current_goal_review"],
#         )
#         print(f"[sales_gpt_api.do output] Full response:\n{sales_utterance_response}")
#         extracted_response = extract_desired_response(sales_utterance_response)
#         print(f"{datetime.now()} Lead Interviewer Statement Generation Returned for call_id: {call_id}")

#         sales_utterance_audio_data, sales_utterance_duration = await tts.generate_speech(extracted_response)
#         print(f"{datetime.now()} Lead Interviewer Audio Generation Returned for call_id: {call_id}")

#         print(f"{datetime.now()} Lead Interviewer Audio to Websocket Begun for call_id: {call_id}")
#         await send_audio(websocket, sales_utterance_audio_data, sales_utterance_duration, call_id)
#         print(f"{datetime.now()} Lead Interviewer Audio to Websocket Returned for call_id: {call_id}")

#         # Calculate timing information
#         end_time = time.time()
#         elapsed_time = end_time - start_time
#         audio_playback_time = play_audio_file_duration + empathy_duration + sales_utterance_duration
#         audio_state_delay = max(0, audio_playback_time - elapsed_time)

#         print(f"{datetime.now()} Generate and Send Speech Returned for call_id: {call_id}")
#         print(f"Elapsed time: {elapsed_time:.2f}s, Audio playback time: {audio_playback_time:.2f}s, Audio state delay: {audio_state_delay:.2f}s")

#         return results.get("empathy_statement", ""), extracted_response, audio_state_delay

#     except Exception as e:
#         print(f"Error in generate_and_send_speech for call_id {call_id}: {e}")
#         print(f"Error in generate_and_send_speech: {type(e).__name__}: {e}")
#         print(traceback.format_exc())

async def generate_and_send_speech(websocket: WebSocket, call_id: str, conversation_history: list, human_response: str, agent_response: str, shared_data: SharedData):
    try:
        start_time = time.time()
        print(f"{datetime.now()} Generate and Send Speech Begun for call_id: {call_id}")
        
        results = {}
        empathy_statement_processed = False
        tts = TextToSpeech()  # Create a single instance of TextToSpeech

        is_first_turn = len(conversation_history) == 0

        play_audio_file_duration = 5.2 if not is_first_turn else 0  # seconds
        empathy_duration = 0
        sales_utterance_duration = 0

        if not is_first_turn:
            asyncio.create_task(play_audio_file(websocket, call_id, shared_data))
        else:
            play_audio_file_duration = 0
        
        sales_gpt_api = call_instances[call_id]["sales_gpt_api"]
        
        async for partial_result in sales_gpt_api.run_chains(conversation_history, human_response, agent_response):
            results.update(partial_result)
            
            if not is_first_turn and "empathy_statement" in partial_result and not empathy_statement_processed:
                print(f"{datetime.now()} Empathy Statement Audio Generation Begun for call_id: {call_id}")
                
                empathy_audio_data, empathy_duration = await tts.generate_speech(results["empathy_statement"])
                print(f"{datetime.now()} Empathy Statement Audio Generation Returned for call_id: {call_id}")
                
                await send_audio(websocket, empathy_audio_data, empathy_duration, call_id, shared_data)
                print(f"{datetime.now()} Empathy Statement Audio Queued for call_id: {call_id}")
                
                empathy_statement_processed = True

        print(f"{datetime.now()} Lead Interviewer Statement Generation Begun for call_id: {call_id}")
        sales_utterance_response = await sales_gpt_api.do(
            conversation_history,
            human_response,
            empathy_statement=results.get("empathy_statement", ""),
            current_goal_review=results["current_goal_review"],
        )
        print(f"[sales_gpt_api.do output] Full response:\n{sales_utterance_response}")
        extracted_response = extract_desired_response(sales_utterance_response)
        print(f"{datetime.now()} Lead Interviewer Statement Generation Returned for call_id: {call_id}")

        sales_utterance_audio_data, sales_utterance_duration = await tts.generate_speech(extracted_response)
        print(f"{datetime.now()} Lead Interviewer Audio Generation Returned for call_id: {call_id}")

        print(f"{datetime.now()} Lead Interviewer Audio to Queue Begun for call_id: {call_id}")
        await send_audio(websocket, sales_utterance_audio_data, sales_utterance_duration, call_id, shared_data)
        print(f"{datetime.now()} Lead Interviewer Audio to Queue Returned for call_id: {call_id}")

        # Wait for all audio to be sent
        while not await shared_data.audio_queue.is_empty():
            await asyncio.sleep(0.1)

        # Clear the queue after all audio has been sent
        await shared_data.audio_queue.clear()
        print(f"{datetime.now()} Audio queue cleared for call_id: {call_id}")

        # Calculate timing information
        end_time = time.time()
        elapsed_time = end_time - start_time
        audio_playback_time = play_audio_file_duration + empathy_duration + sales_utterance_duration
        audio_state_delay = max(0, audio_playback_time - elapsed_time)

        print(f"{datetime.now()} Generate and Send Speech Returned for call_id: {call_id}")
        print(f"Elapsed time: {elapsed_time:.2f}s, Audio playback time: {audio_playback_time:.2f}s, Audio state delay: {audio_state_delay:.2f}s")

        return results.get("empathy_statement", ""), extracted_response, audio_state_delay

    except Exception as e:
        print(f"Error in generate_and_send_speech for call_id {call_id}: {e}")
        print(f"Error in generate_and_send_speech: {type(e).__name__}: {e}")
        print(traceback.format_exc())



def extract_desired_response(response):
    print(f"[extract_desired_response input] Full text received:\n{response}")

    marker = "<<<LEAD_RESPONSE>>>"
    
    start = response.find(marker)
    print(f"Start marker position: {start}")
    
    if start != -1:
        # Look for the next occurrence of the marker
        end = response.find(marker, start + len(marker))
        print(f"End marker position: {end}")
        
        if end != -1:
            # Extract the content between the markers
            extracted = response[start + len(marker):end].strip()
            print(f"Extracted LEAD_RESPONSE: {extracted}")
            return extracted
        else:
            print("Could not find end marker, returning everything after start marker")
            # If no end marker is found, return everything after the start marker
            extracted = response[start + len(marker):].strip()
            print(f"Extracted LEAD_RESPONSE: {extracted}")
            return extracted
    else:
        print("Could not find start marker")
    
    # If the start marker is not found, return the original response
    print(f"Returning original response: {response.strip()}")
    return response.strip()



# async def send_audio(vonage_websocket: WebSocket, audio_data, duration, call_id: str):
#     try:
#         print(f"{datetime.now()} Sending Audio Stream - Begun for call_id: {call_id}")
#         samples = bytearray(audio_data)
#         # Set the buffer size to 6 chunks of 20ms audio (320 * 2 bytes per chunk)
#         buffer_size = int(1 / 0.02)
#         chunk_size = 320 * 2

#         print(f"{datetime.now()} Sending Audio Stream - Begun")
#         while len(samples) >= chunk_size * buffer_size:
#             for i in range(buffer_size):
#                 chunk = samples[i*chunk_size:(i+1)*chunk_size]
#                 await vonage_websocket.send_bytes(chunk)
#                 # print(f"Sent audio chunk of size {len(chunk)} bytes")
#             samples = samples[buffer_size*chunk_size:]
#             await asyncio.sleep(0.018)
        
#         # Send the remaining audio data only if it forms complete chunks of 640 bytes
#         while len(samples) >= chunk_size:
#             chunk = samples[:chunk_size]
#             await vonage_websocket.send_bytes(chunk)
#             # print(f"Sent remaining audio chunk of size {len(chunk)} bytes")
#             samples = samples[chunk_size:]
#             await asyncio.sleep(0.018)
        
#         # If there are any remaining bytes that don't form a complete chunk, send an empty chunk
#         if len(samples) > 0:
#             padding_size = chunk_size - len(samples)
#             padded_chunk = samples + bytearray(padding_size)
#             await vonage_websocket.send_bytes(padded_chunk)


#         print(f"{datetime.now()} Sending Audio Stream - Finished for call_id: {call_id}")

    
#     except Exception as e:
#         logging.error(f"Error in send_audio: {e}")
#         logging.error(f"Error in send_audio: {type(e).__name__}: {e}")
#         logging.error(traceback.format_exc())


# async def send_audio(vonage_websocket: WebSocket, audio_data, duration, call_id: str):
#     try:
#         print(f"{datetime.now()} Sending Audio Stream - Begun for call_id: {call_id}")
#         samples = bytearray(audio_data)
#         chunk_size = 640  # 320 * 2 bytes per chunk (16-bit audio)
#         chunk_duration = 0.018  # 20ms per chunk
#         buffer_duration = 0  # 2 seconds buffer
#         chunks_in_buffer = int(buffer_duration / chunk_duration)

#         print(f"{datetime.now()} Sending Audio Stream - Begun")
#         start_time = time.time()
#         chunk_count = 0

#         # Send the initial 2-second buffer immediately
#         for _ in range(chunks_in_buffer):
#             if len(samples) >= chunk_size:
#                 chunk = samples[:chunk_size]
#                 await vonage_websocket.send_bytes(chunk)
#                 samples = samples[chunk_size:]
#                 chunk_count += 1
#             else:
#                 break

#         # Continue with the regular streaming
#         while samples:
#             chunk = samples[:chunk_size]
#             if len(chunk) < chunk_size:
#                 # Pad the last chunk if it's not full
#                 chunk = chunk.ljust(chunk_size, b'\x00')
            
#             await vonage_websocket.send_bytes(chunk)
#             samples = samples[chunk_size:]
            
#             chunk_count += 1
#             expected_time = start_time + (chunk_count * chunk_duration)
#             current_time = time.time()
            
#             if current_time < expected_time:
#                 await asyncio.sleep(expected_time - current_time)

#         print(f"{datetime.now()} Sending Audio Stream - Finished for call_id: {call_id}")
#         print(f"Sent {chunk_count} chunks, total duration: {chunk_count * chunk_duration:.2f} seconds")

#     except Exception as e:
#         logging.error(f"Error in send_audio: {e}")
#         logging.error(f"Error in send_audio: {type(e).__name__}: {e}")
#         logging.error(traceback.format_exc())

async def send_queued_audio(vonage_websocket: WebSocket, shared_data: SharedData):
    chunk_size = 320 * 2  # 20ms of audio at 16kHz, 16-bit
    delay = 0.018  # 19ms delay

    while True:
        audio_chunk = await shared_data.audio_queue.dequeue()
        if audio_chunk is not None:
            await vonage_websocket.send_bytes(audio_chunk)
            await asyncio.sleep(delay)
        else:
            await asyncio.sleep(0.001)  # Small sleep to prevent busy-waiting


async def send_audio(vonage_websocket: WebSocket, audio_data, duration, call_id: str, shared_data: SharedData):
    try:
        print(f"{datetime.now()} Queueing Audio Stream - Begun for call_id: {call_id}")
        samples = bytearray(audio_data)
        chunk_size = 320 * 2  # 20ms of audio at 16kHz, 16-bit

        while len(samples) >= chunk_size:
            chunk = samples[:chunk_size]
            await shared_data.audio_queue.enqueue(chunk)
            samples = samples[chunk_size:]
        
        if len(samples) > 0:
            padding_size = chunk_size - len(samples)
            padded_chunk = samples + bytearray(padding_size)
            await shared_data.audio_queue.enqueue(padded_chunk)

        print(f"{datetime.now()} Queueing Audio Stream - Finished for call_id: {call_id}")

    except Exception as e:
        logging.error(f"Error in send_audio: {e}")
        logging.error(f"Error in send_audio: {type(e).__name__}: {e}")
        logging.error(traceback.format_exc())



class WebSocketManager:
    def __init__(self, websocket: WebSocket, shared_data: SharedData):
        self.websocket = websocket
        self.shared_data = shared_data
        self.call_id = shared_data.call_id  # Add this line
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 1  # Initial delay in seconds
        self.is_reconnecting = False

    async def connect(self):
        await self.websocket.accept()
        self.shared_data.set_websocket(self.websocket)
        self.shared_data.websocket_ready.set()  # Set the websocket_ready event
        print(f"WebSocket connection accepted for call_id: {self.call_id}")

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
            print(f"Error in WebSocket connection for call_id {self.call_id}: {e}")
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
#     print(f"{datetime.now()}: WebSocket connection opened for call_id: {call_id}")

#     if call_id not in call_instances:
#         print(f"{datetime.now()}: Error: No call instance found for call_id: {call_id}")
#         await websocket.close(code=1000)
#         return

#     shared_data = call_instances[call_id]["shared_data"]
#     websocket_manager = WebSocketManager(websocket, shared_data)
#     await websocket_manager.connect()

#     # Start the audio sending task
#     audio_send_task = asyncio.create_task(send_queued_audio(websocket, shared_data))

#     deepgram = DeepgramClient(os.environ["DEEPGRAM_API_KEY"])
#     dg_connection = deepgram.listen.live.v("1")

#     def on_open(self, open, **kwargs):
#         print(f"{datetime.now()}: Deepgram connection opened for call_id: {call_id}")

#     def on_message(self, result, **kwargs):
#         if result.channel.alternatives[0].words:
#             shared_data.update_word_timestamp()
#         else:
#             shared_data.update_no_word_timestamp()
        
#         handle_transcription(result, shared_data)

#     def on_error(self, error, **kwargs):
#         print(f"{datetime.now()}: Deepgram Error for call_id {call_id}: {error}")

#     def on_close(self, close, **kwargs):
#         print(f"{datetime.now()}: Deepgram connection closed for call_id: {call_id}")

#     dg_connection.on(LiveTranscriptionEvents.Open, on_open)
#     dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
#     dg_connection.on(LiveTranscriptionEvents.Error, on_error)
#     dg_connection.on(LiveTranscriptionEvents.Close, on_close)

#     options = LiveOptions(
#         model="nova-2",
#         punctuate=True,
#         language="en-US",
#         encoding="linear16",
#         channels=1,
#         sample_rate=16000,
#         interim_results=True,
#     )

#     try:
#         dg_connection.start(options)
#         print(f"{datetime.now()}: Deepgram connection started successfully for call_id: {call_id}")

#         audio_packet_count = 0
#         last_audio_time = time.time()

#         while True:
#             try:
#                 message = await websocket_manager.receive_message()
#                 if message["type"] == "websocket.receive":
#                     if "bytes" in message:
#                         audio_data = message["bytes"]
#                         audio_packet_count += 1
#                         current_time = time.time()
                        
#                         dg_connection.send(audio_data)
                        
#                         last_audio_time = current_time
                    
#             except WebSocketDisconnect as e:
#                 logger.error(f"{datetime.now()}: WebSocket disconnected for call_id {call_id}: code={e.code}")
#                 logger.error(f"{datetime.now()}: Disconnection reason for call_id {call_id}: {getattr(e, 'reason', 'Unknown')}")
                
#                 if await websocket_manager.should_reconnect():
#                     print(f"{datetime.now()}: Attempting to reconnect for call_id: {call_id}")
#                     dg_connection = deepgram.listen.live.v("1")
#                     dg_connection.on(LiveTranscriptionEvents.Open, on_open)
#                     dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
#                     dg_connection.on(LiveTranscriptionEvents.Error, on_error)
#                     dg_connection.on(LiveTranscriptionEvents.Close, on_close)
#                     dg_connection.start(options)
#                     print(f"{datetime.now()}: Deepgram connection restarted successfully for call_id: {call_id}")
#                     continue
#                 else:
#                     print(f"{datetime.now()}: Call terminated for call_id: {call_id}. WebSocket will not reconnect.")
#                     break

#     except Exception as e:
#         print(f"{datetime.now()}: Error in WebSocket endpoint for call_id {call_id}: {e}")
#         print(traceback.format_exc())

#     finally:
#             if dg_connection:
#                 dg_connection.finish()
#                 print(f"{datetime.now()}: Deepgram connection closed for call_id: {call_id}")

#             # Cancel the audio sending task
#             audio_send_task.cancel()
#             try:
#                 await audio_send_task
#             except asyncio.CancelledError:
#                 pass

#             try:
#                 if websocket_manager.websocket.client_state.name != "DISCONNECTED":
#                     await websocket_manager.disconnect()
#                     print(f"{datetime.now()}: WebSocket disconnected successfully for call_id: {call_id}")
#             except Exception as e:
#                 print(f"{datetime.now()}: Error closing WebSocket connection for call_id {call_id}: {e}")
#                 print(traceback.format_exc())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, call_id: str = Query(...)):
    print(f"{datetime.now()}: WebSocket connection opened for call_id: {call_id}")

    if call_id not in call_instances:
        print(f"{datetime.now()}: Error: No call instance found for call_id: {call_id}")
        await websocket.close(code=1000)
        return

    shared_data = call_instances[call_id]["shared_data"]
    websocket_manager = WebSocketManager(websocket, shared_data)
    await websocket_manager.connect()

    # Start the audio sending task
    audio_send_task = asyncio.create_task(send_queued_audio(websocket, shared_data))

    # AssemblyAI setup
    URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"

    # Retrieve the AssemblyAI API key from environment variables
    auth_key = os.environ.get("ASSEMBLYAI_API_KEY")

    # Check if auth_key is None or empty
    if not auth_key:
        print(f"{datetime.now()}: Error: ASSEMBLYAI_API_KEY is not set in the environment variables.")
        # Close the WebSocket connection and return
        await websocket.close(code=1000)
        return

    # Initialize audio_buffer in shared_data
    shared_data.audio_buffer = bytearray()

    # Define send and receive functions
    async def send(_ws):
        while True:
            try:
                message_data = await websocket.receive()
                if message_data.get("type") == "websocket.receive" and "bytes" in message_data:
                    # Extract the binary data from the message
                    audio_data = message_data["bytes"]
                    # Append the binary data to the audio_buffer
                    shared_data.audio_buffer.extend(audio_data)

                    # If the audio_buffer has at least 3200 bytes of data (~100ms of audio)
                    if len(shared_data.audio_buffer) >= 3200:
                        # Base64 encode the audio_buffer
                        data = base64.b64encode(shared_data.audio_buffer).decode("utf-8")
                        # Create a JSON string that contains the base64-encoded audio data
                        json_data = json.dumps({"audio_data": data})
                        # Send the JSON string to the AssemblyAI WebSocket connection
                        await _ws.send(json_data)
                        # Reset the audio_buffer to an empty bytearray
                        shared_data.audio_buffer = bytearray()
                else:
                    print(f"{datetime.now()}: Received non-bytes message: {message_data}")
            except Exception as e:
                print(f"{datetime.now()}: Error in send function for call_id {call_id}: {e}")
                print(traceback.format_exc())
                break

    async def receive(_ws):
        while True:
            try:
                result_str = await _ws.recv()
                print(f"{datetime.now()}: Received message from AssemblyAI for call_id {call_id}: {result_str}")
                result = json.loads(result_str)
                if 'text' in result:
                    # Update the word or no-word timestamp
                    if result['text'].strip():
                        shared_data.update_word_timestamp()
                    else:
                        shared_data.update_no_word_timestamp()

                    # Handle transcription
                    if result['message_type'] == 'FinalTranscript' and result['text'].strip():
                        shared_data.add_part(result['text'])
                        print(f"{datetime.now()}: Appending final transcript - {result['text']}")
                    elif result['message_type'] == 'PartialTranscript' and result['text'].strip():
                        print(f"{datetime.now()}: Partial transcript - {result['text']}")
            except Exception as e:
                print(f"{datetime.now()}: Error in receive function for call_id {call_id}: {e}")
                print(traceback.format_exc())
                break

    # Establish connection to AssemblyAI
    try:
        async with websockets.connect(
            URL,
            extra_headers=(("Authorization", auth_key),),
            ping_interval=5,
            ping_timeout=120
        ) as _ws:
            print(f"{datetime.now()}: Connected to AssemblyAI WebSocket for call_id {call_id}")
            await asyncio.gather(send(_ws), receive(_ws))
    except Exception as e:
        print(f"{datetime.now()}: Exception occurred while connecting to AssemblyAI for call_id {call_id}: {e}")
        print(traceback.format_exc())
    finally:
        # Handle exceptions and cleanup
        # Cancel the audio sending task
        audio_send_task.cancel()
        try:
            await audio_send_task
        except asyncio.CancelledError:
            pass

        try:
            if websocket_manager.websocket.client_state.name != "DISCONNECTED":
                await websocket_manager.disconnect()
                print(f"{datetime.now()}: WebSocket disconnected successfully for call_id: {call_id}")
        except Exception as e:
            print(f"{datetime.now()}: Error closing WebSocket connection for call_id {call_id}: {e}")
            print(traceback.format_exc())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)