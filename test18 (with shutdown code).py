from fastapi import FastAPI, HTTPException, Query, Body, WebSocket, Request, WebSocketDisconnect
from starlette.websockets import WebSocketState
from websockets.exceptions import ConnectionClosedError, WebSocketException
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
# # the SalesGPTAPI class is initialised once when the server starts with the config path getting passed in.
# sales_api = SalesGPTAPI(config_path=CONFIG_PATH, verbose=False)

# Load environment variables
load_dotenv()
tracemalloc.start()
app = FastAPI()
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
        self.call_id = None  # Add this line
        self.is_terminating = False  # New attribute to indicate if the call is terminating
        
        # These are for the listening functionality
        self.transcript_parts = []
        self.last_word_time = None
        self.last_no_word_time = None



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
        self.shared_data.set_call_id(call_id)  # Add this line
        self.running = True  # New attribute to control the main loop

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


    async def generate_franko_response(self):
        try:
            print(f"{datetime.now()} Generate Franko Response Begun")

            shared_data = call_instances[call_id]["shared_data"]
            
            if shared_data.is_terminating:  # New: Check is_terminating
                print(f"{datetime.now()} Call is terminating, skipping response generation for call_id: {call_id}")
                return

            # Get conversation history and human response from Redis
            conversation_history = json.loads(self.r.get(f"{self.call_id}_conversation_history").decode("utf-8"))
            human_response = self.r.get(f'{self.call_id}_human_response')
            human_response = human_response.decode("utf-8") if human_response else "N/A"
            agent_response = self.r.get(f'{self.call_id}_agent_response')
            agent_response = agent_response.decode("utf-8") if agent_response else "N/A"

            # Pass the websocket object and conversation data to the generate_and_send_speech function
            empathy_statement, extracted_response, sales_utterance_duration = await generate_and_send_speech(
                self.shared_data.get_websocket(), 
                self.call_id,  # Add this line to pass the call_id
                conversation_history, 
                human_response, 
                agent_response
            )

            if shared_data.is_terminating:  # New: Check is_terminating again after long operation
                print(f"{datetime.now()} Call terminated during response generation for call_id: {call_id}")
                return

            agent_name = "Franko"
            ai_message = f"{agent_name}: {empathy_statement} {extracted_response}"

            # Print the full AI message with breaks
            print(f"\nFull AI Message:\n{ai_message}\n")

            clean_ai_message = strip_break_tags(ai_message)

            # Print the cleaned AI message
            print(f"\nCleaned AI Message:\n{clean_ai_message}\n")

            self.r.set(f'{self.call_id}_agent_response', clean_ai_message)
            conversation_history.append(clean_ai_message)
            self.r.set(f'{self.call_id}_conversation_history', json.dumps(conversation_history))

            # Run the update_conversation_stage method as a separate task
            print(f"{datetime.now()} Update Conversation Stage (same as determine but in test14 file) Begun")
            asyncio.create_task(self.update_conversation_stage())
            # print(f"Updating conversation stage in the background")

            # print(f"Sleep to allow audio to play starting...")
            await asyncio.sleep(max(sales_utterance_duration - 2, 0))
            # print(f"Sleep to allow audio to play ending...")

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

    def stop(self):  # New method to stop the state machine
        self.running = False

    async def start(self):
        await self.call_setup()
        await self.listen()

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
    call_id = shared_data.call_id  # Add this line

    if result.is_final and result.channel.alternatives[0].words:
        shared_data.add_part(sentence)
        print(f"{datetime.now()}: Appending partial transcript - {sentence}")


def strip_break_tags(text):
    return re.sub(r'<break\s+time="[^"]*"\s*/>', '', text)


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
            "text": text,
            "voice_settings": {
                "similarity_boost": 1,
                "stability": 1
            }
        }
        try:
            response = requests.post(ELEVENLABS_URL, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            print(f"Time taken for ElevenLabs API request: {time.time() - start_time} seconds")
            
            audio_content = response.content
            duration = self.calculate_audio_duration(audio_content)
            
            return audio_content, duration
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTPError during ElevenLabs API request: {e.response.status_code} {e.response.text}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error during ElevenLabs API request: {e}")
        print(f"Failed to generate speech for text: {text}")
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
async def make_outgoing_call():
    try:
        call_id = str(uuid4())
        print(f"{datetime.now()}: Call initiated with call_id: {call_id}")

        # Store call-related data in Redis
        r.set(f'{call_id}_call_answered', 'False')
        r.set(f'{call_id}_human_response', "")
        r.set(f'{call_id}_agent_response', "")
        r.set(f'{call_id}_conversation_history', json.dumps([]))

        # Create new instances for this call
        sales_gpt_api = SalesGPTAPI(config_path=CONFIG_PATH, call_id=call_id)
        sales_gpt = sales_gpt_api.initialize_agent()
        shared_data = SharedData()
        state_machine = StateMachine(call_id=call_id, r=r, vonage_client=vonage_client, shared_data=shared_data, sales_api=sales_gpt_api)

        # Store instances in the dictionary
        call_instances[call_id] = {
            "sales_gpt_api": sales_gpt_api,
            "sales_gpt": sales_gpt,
            "shared_data": shared_data,
            "state_machine": state_machine
        }

        # Start the state machine asynchronously
        asyncio.create_task(state_machine.start())

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
        
        elif call_status.status == 'completed':
            print(f"{datetime.now()}: Call completed, initiating termination for call_id: {call_id}")
            await terminate_call(call_id)  # New: Call terminate_call when status is 'completed'
        
        else:
            print(f"{datetime.now()}: Unhandled call status: {call_status.status} for call_id: {call_id}")
        
    except Exception as e:
        print(f"{datetime.now()}: Error in handle_vonage_call_status for call_id: {call_id}: {e}")
        print(traceback.format_exc())
    
    return {"message": "Status update received"}




async def terminate_call(call_id: str):
    if call_id in call_instances:
        try:
            print(f"{datetime.now()}: Starting termination for call_id: {call_id}")

            # Get instances from call_instances
            shared_data = call_instances[call_id]["shared_data"]
            state_machine = call_instances[call_id]["state_machine"]  # New: Get state_machine instance

            # Set the termination flag
            shared_data.is_terminating = True  # New: Set is_terminating flag
            state_machine.stop()  # New: Stop the state machine

            # Delay the execution by 2 seconds to allow ongoing processes to complete
            await asyncio.sleep(3)

            # Clean up the SharedData instance
            shared_data.reset()
            print(f"{datetime.now()}: SharedData instance reset for call_id: {call_id}")

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





@app.post("/vonage_recording")
async def handle_recording(request: Request, call_id: str = Query(...)):
    data = await request.json()
    recording_url = data.get('recording_url')

    if recording_url:
        try:
            if call_id not in call_instances:
                raise Exception(f"No call instance found for call_id: {call_id}")

            shared_data = call_instances[call_id]["shared_data"]

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
                raise Exception(f"Failed to upload recording for call_id {call_id}: {upload_response.text}")

            # Construct the Supabase URL for the uploaded file
            supabase_url = f"https://cedxguhjiaxatqwsccrp.supabase.co/storage/v1/object/public/recordings/Franko_Test/{call_id}.mp3"
            # Save the Supabase URL to the shared_data instance
            shared_data.recording_url = supabase_url
            print(f"Supabase URL for call_id {call_id}: {supabase_url}")

            print(f"Recording URL saved to Supabase successfully for call_id {call_id}")
        except Exception as e:
            print(f"Exception occurred while saving recording URL for call_id {call_id}: {e}")
            print(traceback.format_exc())
            raise HTTPException(status_code=500, detail=str(e))
    else:
        print(f"No recording URL found in the request data for call_id {call_id}")
        raise HTTPException(status_code=400, detail="No recording URL provided")

    return {"message": f"Recording processed successfully for call_id {call_id}"}









# # Production
# async def play_audio_file(websocket: WebSocket, call_id: str):
#     # Specify the exact file path
#     audio_folder_path = "/mnt/buffer_audio"
#     audio_file_name = "understood_okay_audio.raw"
#     audio_file_path = os.path.join(audio_folder_path, audio_file_name)

# Local
async def play_audio_file(websocket: WebSocket, call_id: str):
    audio_file_name = "understood_okay_audio.raw"
    audio_folder_path = r"C:\Users\fletc\Desktop\Franko - 06\SalesGPT\buffer_audio"  # Update this path
    audio_file_path = os.path.join(audio_folder_path, audio_file_name)
    
    try:
        print(f"[{datetime.now()}] - Sending Audio Buffer File Begun for call_id {call_id}: {audio_file_path}")
        
        with open(audio_file_path, 'rb') as f:
            audio_data = f.read()
        await send_audio(websocket, audio_data, 0, call_id)  # Pass call_id here
        print(f"[{datetime.now()}] - Sending Audio Buffer File Returned for call_id {call_id}")
    except FileNotFoundError:
        print(f"Error: Audio file not found at {audio_file_path} for call_id {call_id}")
    except Exception as e:
        print(f"Error playing audio file for call_id {call_id}: {e}")

        



async def generate_and_send_speech(websocket: WebSocket, call_id: str, conversation_history: list, human_response: str, agent_response: str):
    try:
        print(f"{datetime.now()} Generate and Send Speech Begun for call_id: {call_id}")
        
        results = {}
        empathy_statement_processed = False

        # Check if it's the first turn in the conversation
        is_first_turn = len(conversation_history) == 0

        # Only play the audio file if it's not the first turn
        if not is_first_turn:
            # Start playing the audio file asynchronously without awaiting
            asyncio.create_task(play_audio_file(websocket, call_id))
        
        sales_gpt_api = call_instances[call_id]["sales_gpt_api"]
        
        async for partial_result in sales_gpt_api.run_chains(conversation_history, human_response, agent_response):
            results.update(partial_result)
            
            if "empathy_statement" in partial_result and not empathy_statement_processed:
                print(f"{datetime.now()} Empathy Statement Audio Generation Begun for call_id: {call_id}")
                empathy_audio_data, empathy_duration = TextToSpeech().generate_speech(results["empathy_statement"])
                print(f"{datetime.now()} Empathy Statement Audio Generation Returned for call_id: {call_id}")
                
                await send_audio(websocket, empathy_audio_data, empathy_duration, call_id)
                print(f"{datetime.now()} Empathy Statement Audio Sent for call_id: {call_id}")
                
                empathy_statement_processed = True

        # Generate sales utterance audio
        print(f"{datetime.now()} Lead Interviewer Statement Generation Begun for call_id: {call_id}")
        sales_utterance_response = await sales_gpt_api.do(
            conversation_history,
            human_response,
            empathy_statement=results["empathy_statement"],
            key_points=results["key_points"],
            current_goal_review=results["current_goal_review"],
        )
        extracted_response = extract_desired_response(sales_utterance_response)
        print(f"{datetime.now()} Lead Interviewer Statement Generation Returned for call_id: {call_id}")

        sales_utterance_audio_data, sales_utterance_duration = TextToSpeech().generate_speech(extracted_response)
        print(f"{datetime.now()} Lead Interviewer Audio Generation Returned for call_id: {call_id}")

        print(f"{datetime.now()} Lead Interviewer Audio to Websocket Begun for call_id: {call_id}")
        await send_audio(websocket, sales_utterance_audio_data, sales_utterance_duration, call_id)
        print(f"{datetime.now()} Lead Interviewer Audio to Websocket Returned for call_id: {call_id}")

        print(f"{datetime.now()} Generate and Send Speech Returned for call_id: {call_id}")
        return results.get("empathy_statement"), extracted_response, sales_utterance_duration

    except Exception as e:
        print(f"Error in generate_and_send_speech for call_id {call_id}: {e}")
        print(f"Error in generate_and_send_speech: {type(e).__name__}: {e}")
        print(traceback.format_exc())


def extract_desired_response(response):
    start_marker = "<<<LEAD>>>"
    end_marker = "<<<LEAD>>>"
    
    start = response.find(start_marker)
    end = response.rfind(end_marker)
    
    if start != -1 and end != -1 and start < end:
        # Extract the content between the markers
        extracted = response[start + len(start_marker):end].strip()
        return extracted
    else:
        # If the markers are not found, return the original response
        return response



async def send_audio(vonage_websocket: WebSocket, audio_data, duration, call_id: str):
    try:
        print(f"{datetime.now()} Sending Audio Stream - Begun for call_id: {call_id}")
        samples = bytearray(audio_data)
        buffer_size = int(1 / 0.02)
        chunk_size = 320 * 2

        shared_data = call_instances[call_id]["shared_data"]  # New: Get shared_data

        print(f"{datetime.now()} Sending Audio Stream - Begun")
        while len(samples) >= chunk_size * buffer_size and not shared_data.is_terminating:  # New: Check is_terminating
            for i in range(buffer_size):
                if shared_data.is_terminating:  # New: Check is_terminating
                    break
                chunk = samples[i*chunk_size:(i+1)*chunk_size]
                await vonage_websocket.send_bytes(chunk)
            samples = samples[buffer_size*chunk_size:]
            await asyncio.sleep(0.018)
        
        # Send remaining audio data only if not terminating
        while len(samples) >= chunk_size and not shared_data.is_terminating:  # New: Check is_terminating
            chunk = samples[:chunk_size]
            await vonage_websocket.send_bytes(chunk)
            samples = samples[chunk_size:]
            await asyncio.sleep(0.018)
        
        print(f"{datetime.now()} Sending Audio Stream - Finished for call_id: {call_id}")

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
        print(f"WebSocket disconnected for call_id: {self.call_id}")

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

    deepgram = DeepgramClient(os.environ["DEEPGRAM_API_KEY"])
    dg_connection = deepgram.listen.live.v("1")

    def on_open(self, open, **kwargs):
        print(f"{datetime.now()}: Deepgram connection opened for call_id: {call_id}")

    def on_message(self, result, **kwargs):
        if result.channel.alternatives[0].words:
            shared_data.update_word_timestamp()
        else:
            shared_data.update_no_word_timestamp()
        
        handle_transcription(result, shared_data)

    def on_error(self, error, **kwargs):
        print(f"{datetime.now()}: Deepgram Error for call_id {call_id}: {error}")

    def on_close(self, close, **kwargs):
        print(f"{datetime.now()}: Deepgram connection closed for call_id: {call_id}")

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
        print(f"{datetime.now()}: Deepgram connection started successfully for call_id: {call_id}")

        while not shared_data.is_terminating:  # New: Check is_terminating flag
            try:
                message = await websocket_manager.receive_message()
                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        audio_data = message["bytes"]
                        dg_connection.send(audio_data)
                    
            except WebSocketDisconnect as e:
                logger.error(f"{datetime.now()}: WebSocket disconnected for call_id {call_id}: code={e.code}")
                logger.error(f"{datetime.now()}: Disconnection reason for call_id {call_id}: {getattr(e, 'reason', 'Unknown')}")
                
                if await websocket_manager.should_reconnect():
                    print(f"{datetime.now()}: Attempting to reconnect for call_id: {call_id}")
                    dg_connection = deepgram.listen.live.v("1")
                    dg_connection.on(LiveTranscriptionEvents.Open, on_open)
                    dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
                    dg_connection.on(LiveTranscriptionEvents.Error, on_error)
                    dg_connection.on(LiveTranscriptionEvents.Close, on_close)
                    dg_connection.start(options)
                    print(f"{datetime.now()}: Deepgram connection restarted successfully for call_id: {call_id}")
                    continue
                else:
                    print(f"{datetime.now()}: Call terminated for call_id: {call_id}. WebSocket will not reconnect.")
                    break

    except Exception as e:
        print(f"{datetime.now()}: Error in WebSocket endpoint for call_id {call_id}: {e}")
        print(traceback.format_exc())

    finally:
        if dg_connection:
            dg_connection.finish()
            print(f"{datetime.now()}: Deepgram connection closed for call_id: {call_id}")

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