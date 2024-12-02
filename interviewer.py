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
from salesgpt.salesgptapi import SalesGPTAPI
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

import aiofiles
from asyncio import Queue
from typing import Optional
from audio_constants import AUDIO_CONSTANTS  # Direct import instead of relative


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


# # Initialize Vonage client
# vonage_client = VonageClient(
#     application_id=VONAGE_APPLICATION_ID,
#     private_key=VONAGE_APPLICATION_PRIVATE_KEY_PATH,
# )
# voice = Voice(vonage_client)

# Add at the top with other global variables
processed_call_completions = set()

# Define a model for incoming call requests with required fields
class CallRequest(BaseModel):
    client_name: str          # Name of the client making the request
    interviewee_name: str     # First name of the person being interviewed
    interviewee_last_name: str # Last name of the person being interviewed
    interviewee_email: str    # Email address of the interviewee
    interviewee_number: str   # Phone number to call
    client_company_description: str  # Description of the client's company
    agent_name: str           # Name of the AI agent
    voice_id: str            # ID for the voice to be used
    unique_customer_identifier: str  # Unique identifier for the customer
    use_case: str            # Use case for this specific call

# Define a model for call status updates from Vonage
class CallStatus(BaseModel):
    headers: dict            # HTTP headers from the status update
    from_: str = Field(alias="from")  # Source phone number (using alias due to 'from' being a Python keyword)
    to: str                  # Destination phone number
    uuid: str               # Unique identifier for the call
    conversation_uuid: str   # Unique identifier for the conversation
    status: str             # Current status of the call
    direction: str          # Direction of the call (inbound/outbound)
    timestamp: str          # Timestamp of the status update

# Define possible states for the call state machine
class CallState(Enum):
    CALL_SETUP = "CALL_SETUP"                          # Initial state when setting up the call
    GENERATE_FRANKO_RESPONSE = "GENERATE_FRANKO_RESPONSE"    # State for generating AI response
    LISTEN_FOR_USER_RESPONSE = "LISTEN_FOR_USER_RESPONSE"    # State for listening to user input

# Class to manage a thread-safe queue for audio data
class AudioQueue:
    def __init__(self):
        self.queue = deque()         # Initialize a double-ended queue for audio data
        self.lock = asyncio.Lock()   # Create a lock for thread-safe operations

    async def enqueue(self, audio_data):
        async with self.lock:        # Acquire lock before modifying queue
            self.queue.append(audio_data)  # Add audio data to queue

    async def dequeue(self):
        async with self.lock:        # Acquire lock before accessing queue
            return self.queue.popleft() if self.queue else None  # Remove and return first item if queue not empty

    async def is_empty(self):
        async with self.lock:        # Acquire lock before checking queue
            return len(self.queue) == 0  # Return True if queue is empty

    async def clear(self):
        async with self.lock:        # Acquire lock before clearing queue
            self.queue.clear()       # Remove all items from queue


class BufferStats:
    def __init__(self):
        self.underruns = 0
        self.overflows = 0
        self.total_samples = 0
        self.late_samples = 0
        self.early_samples = 0
        self.buffer_levels = []
        self.last_update = time.time()

    def update_buffer_level(self, current_level):
        self.buffer_levels.append(current_level)
        if len(self.buffer_levels) > 1000:  # Keep last 1000 measurements
            self.buffer_levels.pop(0)

    def record_underrun(self):
        self.underruns += 1

    def record_overflow(self):
        self.overflows += 1

    def record_sample_timing(self, is_late: bool):
        self.total_samples += 1
        if is_late:
            self.late_samples += 1
        else:
            self.early_samples += 1

    def get_average_buffer_level(self):
        if not self.buffer_levels:
            return 0
        return sum(self.buffer_levels) / len(self.buffer_levels)

    def get_buffer_stability(self):
        if len(self.buffer_levels) < 2:
            return 1.0
        variations = [abs(self.buffer_levels[i] - self.buffer_levels[i-1]) 
                     for i in range(1, len(self.buffer_levels))]
        return 1.0 / (1.0 + sum(variations) / len(variations))

    def log_stats(self):
        current_time = time.time()
        elapsed = current_time - self.last_update
        print(f"""Buffer Statistics:
            Time Period: {elapsed:.2f}s
            Underruns: {self.underruns}
            Overflows: {self.overflows}
            Total Samples: {self.total_samples}
            Late Samples: {self.late_samples}
            Early Samples: {self.early_samples}
            Average Buffer Level: {self.get_average_buffer_level():.2f}
            Buffer Stability: {self.get_buffer_stability():.2f}
        """)
        self.last_update = current_time


class AudioBuffer:
    def __init__(self):
        self.min_buffer_duration = 1.0     # Reduced to 1 second
        self.max_buffer_duration = 4.0     # Reduced to 3 seconds
        self.target_buffer_duration = 2.5  # Reduced to 2 seconds
        self.sample_rate = 16000         
        self.buffer = deque(maxlen=int(self.max_buffer_duration * self.sample_rate))
        self.stats = BufferStats()
        self.lock = asyncio.Lock()
        self.underrun_threshold = 0.2    # Reduced threshold
        
    async def fill_initial_buffer(self):
        """Wait until initial buffer is filled"""
        initial_samples = int(self.min_buffer_duration * self.sample_rate)
        timeout = self.max_buffer_duration * 1.5  # Increased timeout
        start_time = time.time()
        
        while len(self.buffer) < initial_samples:
            if time.time() - start_time > timeout:
                print(f"{datetime.now()} Buffer fill timeout reached")
                break
            await asyncio.sleep(0.01)
            
        # New: Log initial buffer state
        print(f"{datetime.now()} Initial buffer filled: {len(self.buffer)} samples")

    async def adjust_buffer_size(self):
        """Dynamically adjust buffer size based on performance"""
        async with self.lock:
            current_size = len(self.buffer)
            target_samples = int(self.target_buffer_duration * self.sample_rate)
            
            self.stats.update_buffer_level(current_size / target_samples)
            
            if current_size < int(self.min_buffer_duration * self.sample_rate):
                self.stats.record_underrun()
            elif current_size > int(self.max_buffer_duration * self.sample_rate):
                self.stats.record_overflow()

    def is_underrun(self):
        """Check if buffer is in underrun state"""
        return len(self.buffer) < int(self.min_buffer_duration * self.sample_rate)

    def is_overflow(self):
        """Check if buffer is in overflow state"""
        return len(self.buffer) > int(self.max_buffer_duration * self.sample_rate)

    def has_timing_drift(self):
        """Check for significant timing drift"""
        if not self.stats.buffer_levels:
            return False
        
        # Calculate drift based on buffer level stability
        stability = self.stats.get_buffer_stability()
        return stability < 0.8  # Threshold for considering drift significant


class AudioTiming:
    def __init__(self):
        self.drift_samples = 0
        self.last_timestamp = None
        self.adjustment_threshold = 0.005  # 5ms
        self.sample_rate = 16000
        self.stats = BufferStats()

    async def calculate_next_chunk_time(self, nominal_duration):
        now = time.time()
        
        if self.last_timestamp:
            actual_duration = now - self.last_timestamp
            drift = actual_duration - nominal_duration
            self.drift_samples += drift
            
            # Log timing statistics
            self.stats.record_sample_timing(drift > 0)
            
            if abs(self.drift_samples) > self.adjustment_threshold:
                # Adjust timing to compensate for drift
                adjusted_duration = nominal_duration - (self.drift_samples / 2)
                self.drift_samples /= 2  # Gradually correct drift
                return max(0.001, adjusted_duration)  # Ensure positive duration
        
        self.last_timestamp = now
        return nominal_duration

    def reset_timing(self):
        self.drift_samples = 0
        self.last_timestamp = None


class JitterBuffer:
    def __init__(self):
        self.buffer_size = 5  # Number of chunks to buffer before playback
        self.buffer = deque(maxlen=self.buffer_size)
        self.min_fill_level = 3  # Minimum chunks before starting playback

    async def add_chunk(self, chunk):
        self.buffer.append(chunk)

    async def get_chunk(self):
        if len(self.buffer) >= self.min_fill_level:
            return self.buffer.popleft()
        return None


class EnhancedAudioQueue:
    def __init__(self, max_size=1000):  # Reduced queue size
        self.queue = asyncio.Queue(maxsize=max_size)
        self.stats = BufferStats()

    async def enqueue(self, audio_data):
        try:
            await self.queue.put(audio_data)
            self.stats.update_buffer_level(self.queue.qsize())
            # print(f"{datetime.now()} Enqueued audio chunk of size {len(audio_data)}")
        except Exception as e:
            print(f"Error enqueueing audio: {e}")
            print(traceback.format_exc())

    async def dequeue(self):
        try:
            if not self.queue.empty():
                chunk = await self.queue.get()
                self.stats.update_buffer_level(self.queue.qsize())
                return chunk
            return None
        except Exception as e:
            print(f"Error dequeueing audio: {e}")
            print(traceback.format_exc())
            return None

    async def is_empty(self):
        return self.queue.empty()

    def get_buffer_level(self):
        return self.queue.qsize()

    async def handle_backpressure(self):
        """Handle queue overflow condition"""
        print(f"{datetime.now()}: Applying backpressure - Queue size: {len(self.queue)}")
        await asyncio.sleep(0.01)  # Small delay to allow queue to drain

    def get_fill_level(self):
        """Return current queue fill level as a percentage"""
        return len(self.queue) / self.queue.maxlen if self.queue.maxlen else 0

    async def clear(self):
        """Clear all items from the queue."""
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except asyncio.QueueEmpty:
                break




class AudioPlaybackMonitor:
    def __init__(self):
        self.underrun_count = 0
        self.last_error_time = None
        self.recovery_strategies = {
            'underrun': self.handle_underrun,
            'overflow': self.handle_overflow,
            'timing_drift': self.handle_timing_drift
        }
        self.min_recovery_interval = 0.1  # Minimum time between recovery actions
        self.max_underruns = 5  # Maximum underruns before aggressive recovery

    async def handle_underrun(self):
        """Handle buffer underrun condition"""
        current_time = time.time()
        
        # Check if enough time has passed since last recovery action
        if (self.last_error_time is None or 
            current_time - self.last_error_time > self.min_recovery_interval):
            
            self.underrun_count += 1
            self.last_error_time = current_time
            
            if self.underrun_count > self.max_underruns:
                # Aggressive recovery for persistent underruns
                print(f"{datetime.now()}: Performing aggressive underrun recovery")
                await self.aggressive_recovery()
            else:
                # Normal recovery
                print(f"{datetime.now()}: Performing normal underrun recovery")
                await self.normal_recovery()

    async def handle_overflow(self):
        """Handle buffer overflow condition"""
        current_time = time.time()
        
        if (self.last_error_time is None or 
            current_time - self.last_error_time > self.min_recovery_interval):
            
            self.last_error_time = current_time
            print(f"{datetime.now()}: Handling buffer overflow")
            
            # Implement overflow recovery strategy
            await self.reduce_buffer_size()

    async def handle_timing_drift(self):
        """Handle timing drift issues"""
        current_time = time.time()
        
        if (self.last_error_time is None or 
            current_time - self.last_error_time > self.min_recovery_interval):
            
            self.last_error_time = current_time
            print(f"{datetime.now()}: Correcting timing drift")
            
            # Implement timing drift correction
            await self.adjust_timing()

    async def aggressive_recovery(self):
        """Aggressive recovery strategy for persistent underruns"""
        # Reset underrun counter
        self.underrun_count = 0
        
        # Implement aggressive recovery actions
        # For example: increase buffer size significantly, adjust timing parameters
        print(f"{datetime.now()}: Implementing aggressive recovery measures")
        await asyncio.sleep(0.1)  # Allow time for recovery actions

    async def normal_recovery(self):
        """Normal recovery strategy for occasional underruns"""
        # Implement normal recovery actions
        # For example: slight increase in buffer size
        print(f"{datetime.now()}: Implementing normal recovery measures")
        await asyncio.sleep(0.05)  # Allow time for recovery actions

    async def reduce_buffer_size(self):
        """Handle buffer overflow by reducing buffer size"""
        print(f"{datetime.now()}: Reducing buffer size to handle overflow")
        await asyncio.sleep(0.05)  # Allow time for buffer adjustment

    async def adjust_timing(self):
        """Adjust timing parameters to handle drift"""
        print(f"{datetime.now()}: Adjusting timing parameters")
        await asyncio.sleep(0.05)  # Allow time for timing adjustment

    async def monitor_playback(self, buffer_state):
        """Monitor playback and trigger appropriate recovery strategies"""
        try:
            if buffer_state.is_underrun():
                await self.recovery_strategies['underrun']()
            elif buffer_state.is_overflow():
                await self.recovery_strategies['overflow']()
            elif buffer_state.has_timing_drift():
                await self.recovery_strategies['timing_drift']()
                
        except Exception as e:
            print(f"Error in monitor_playback: {e}")
            print(traceback.format_exc())

    def reset_stats(self):
        """Reset monitoring statistics"""
        self.underrun_count = 0
        self.last_error_time = None


class AudioChunkBatcher:
    def __init__(self, target_batch_size=1600):
        self.batch_buffer = []
        self.target_size = target_batch_size
        self.stats = BufferStats()

    async def add_chunk(self, chunk):
        try:
            self.batch_buffer.extend(chunk)
            if len(self.batch_buffer) >= self.target_size:
                return self.flush()
            return None
        except Exception as e:
            print(f"Error in chunk batcher: {e}")
            print(traceback.format_exc())
            return None

    def flush(self):
        try:
            if not self.batch_buffer:
                return None
            batch = bytes(self.batch_buffer)
            self.batch_buffer = []
            self.stats.record_sample_timing(False)  # Record normal timing
            return batch
        except Exception as e:
            print(f"Error flushing batch: {e}")
            self.batch_buffer = []  # Clear buffer on error
            return None


class VonageNumberManager:
    def __init__(self):
        self.numbers = []
        self.current_index = 0
        self.in_use_numbers = set()
        self.initialize_numbers()

    def initialize_numbers(self):
        """Initialize numbers from environment variables"""
        # Get all environment variables that start with VONAGE_NUMBER
        for i in range(1, 6):  # Assuming you have up to 5 numbers
            # Update this line to match your .env format
            number_key = f"VONAGE_NUMBER{str(i).zfill(2)}"  # This will create VONAGE_NUMBER01, VONAGE_NUMBER02, etc.
            number = os.environ.get(number_key)
            if number:
                print(f"Found Vonage number: {number} for key: {number_key}")
                self.numbers.append(number)
            
        if not self.numbers:
            print("Warning: No Vonage numbers found in environment variables")
            raise ValueError("No Vonage numbers found in environment variables")
        
        print(f"Initialized with Vonage numbers: {self.numbers}")

    async def get_available_number(self):
        """Get the next available number using round-robin"""
        try:
            if not self.numbers:
                raise ValueError("No Vonage numbers available")
            
            # Get next number using round-robin
            number = self.numbers[self.current_index]
            print(f"Retrieved number from pool: {number}")
            
            # Update index for next time
            self.current_index = (self.current_index + 1) % len(self.numbers)
            
            # Track number as in use
            self.in_use_numbers.add(number)
            
            return number
            
        except Exception as e:
            print(f"Error getting available number: {e}")
            print(f"Falling back to VONAGE_NUMBER01")
            fallback_number = os.environ.get("VONAGE_NUMBER01")
            if not fallback_number:
                raise ValueError("No fallback Vonage number available")
            return fallback_number

    def release_number(self, number):
        """Release a number from being marked as in use"""
        if number in self.in_use_numbers:
            self.in_use_numbers.remove(number)


# Initialize the VonageNumberManager at the module level
vonage_number_manager = VonageNumberManager()


# Class to store shared data across different components of the system
class SharedData:
    def __init__(self):
        self._data = {}              # Dictionary to store miscellaneous data
        self.websocket = None        # WebSocket connection instance
        self.websocket_ready = asyncio.Event()  # Event to signal when WebSocket is ready
        self.call_completed = False   # Flag to track if call is completed
        self.state_machine = None     # Reference to the state machine
        self.is_reconnecting = False  # Flag to track reconnection status
        self.reconnection_attempts = 0  # Counter for reconnection attempts
        self.call_id = None          # Unique identifier for the call
        
        # Variables for tracking speech recognition
        self.transcript_parts = []    # List to store partial transcripts
        self.last_word_time = None    # Timestamp of last word detected
        self.last_no_word_time = None # Timestamp of last silence detected
        self.empty_transcript_count = 0  # Add counter for empty transcripts
        self.audio_lock = asyncio.Lock()  # Add this line

        # Audio processing components
        self.audio_queue = Queue()  # Queue for managing audio data
        self.audio_sending_completed = asyncio.Event()  # Event to signal when audio sending is done

        # Add new audio components
        self.audio_buffer = AudioBuffer()
        self.audio_timing = AudioTiming()
        self.audio_queue = EnhancedAudioQueue()
        self.audio_monitor = AudioPlaybackMonitor()
        self.chunk_batcher = AudioChunkBatcher()

        # Performance monitoring
        self.performance_stats = {
            'buffer_underruns': 0,
            'buffer_overflows': 0,
            'timing_drifts': 0,
            'total_chunks_processed': 0,
            'start_time': time.time()
        }

        self.silence_detection_task = None
        self.last_audio_time = datetime.now()

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
        """Update timestamp when we receive actual words"""
        self.last_word_time = datetime.now()
        self.empty_transcript_count = 0  # Reset empty transcript counter

    def update_no_word_timestamp(self):
        """Update timestamp when we receive empty transcript"""
        self.last_no_word_time = datetime.now()
        self.empty_transcript_count += 1
        if self.empty_transcript_count % 5 == 0:  # Log every 5th empty transcript
            print(f"{datetime.now()}: Received {self.empty_transcript_count} empty transcripts")

    def reset_transcripts(self):
        self.transcript_parts = []
        self.last_word_time = None
        self.last_no_word_time = None
        self.empty_transcript_count = 0

    async def monitor_silence(self):
        while not self.call_completed:
            current_time = datetime.now()
            time_since_last_audio = (current_time - self.last_audio_time).total_seconds()
            
            if time_since_last_audio > 0.1:  # 100ms without audio
                self.update_no_word_timestamp()
            
            await asyncio.sleep(0.1)

    def update_audio_time(self):
        self.last_audio_time = datetime.now()


    def reset(self):
        """Reset all instance variables to their initial state"""
        self._data = {}
        self.websocket = None
        self.websocket_ready = asyncio.Event()
        self.call_completed = False
        self.state_machine = None
        self.is_reconnecting = False
        self.reconnection_attempts = 0
        self.call_id = None
        
        # # Reset speech recognition variables
        # self.transcript_parts = []
        # self.last_word_time = None
        # self.last_no_word_time = None
        # self.empty_transcript_count = 0
        
        # Reset audio components
        self.audio_queue = Queue()
        self.audio_sending_completed = asyncio.Event()
        self.audio_buffer = AudioBuffer()
        self.audio_timing = AudioTiming()
        self.audio_queue = EnhancedAudioQueue()
        self.audio_monitor = AudioPlaybackMonitor()
        self.chunk_batcher = AudioChunkBatcher()
        
        # Reset silence detection
        self.silence_detection_task = None
        self.last_audio_time = datetime.now()


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
            empathy_statement, extracted_response, audio_state_delay, audio_playback_time = await generate_and_send_speech(
                self.shared_data.get_websocket(), 
                self.call_id,  # Add this line to pass the call_id
                conversation_history, 
                human_response, 
                agent_response,
                self.shared_data  # Add this line to pass shared_data
            )

            # Get the current timestamp in minutes since the start of the call
            current_time = time.time() - audio_playback_time
            interview_start_time = self.sales_api.sales_agent.interview_start_time
            elapsed_seconds = current_time - interview_start_time
            minutes = int(elapsed_seconds // 60)
            seconds = int(elapsed_seconds % 60)
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
                
            agent_name = self.sales_api.config.get('agent_name', 'Agent')
            ai_message = f"{empathy_statement} {extracted_response}"

            # Print the full AI message with breaks
            print(f"\nFull AI Message:\n{ai_message}\n")

            clean_ai_message = strip_break_tags(ai_message)

            # Format the agent's response with HTML line breaks
            timestamped_ai_message = f"{agent_name}: {clean_ai_message} {timestamp}"

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
    
        # Get the current timestamp in minutes:seconds format
        current_time = time.time()
        interview_start_time = self.sales_api.sales_agent.interview_start_time
        elapsed_seconds = current_time - interview_start_time
        minutes = int(elapsed_seconds // 60)
        seconds = int(elapsed_seconds % 60)
        timestamp = f"[{minutes:02d}:{seconds:02d}]"

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

        # Format the human input with HTML line breaks
        human_input = f"{interviewee_name}: {full_transcript.strip()} {timestamp}"

        conversation_history = json.loads(self.r.get(f'{self.call_id}_conversation_history').decode("utf-8"))
        conversation_history.append(human_input)
        self.r.set(f'{self.call_id}_conversation_history', json.dumps(conversation_history))
        
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
    """Check if we've received empty transcripts after the last word"""
    if last_word_time:  # If we've received words before
        if last_no_word_time and last_no_word_time > last_word_time:  # And we're getting empty transcripts
            time_diff = last_no_word_time - last_word_time
            empty_transcript_duration = time_diff > timedelta(seconds=2.0)
            if empty_transcript_duration:
                print(f"{datetime.now()}: Empty transcripts detected for {time_diff.total_seconds()} seconds")
            return empty_transcript_duration
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
    # Class for handling text-to-speech conversion using ElevenLabs API

    # Load API key from environment variables
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    
    def __init__(self, voice_id=None):
        # Initialize with a default voice ID that can be overridden
        self.voice_id = voice_id or "IKne3meq5aSn9XLyUdCD"  # Default to Charlie voice if none provided

    async def generate_speech(self, text):
        # Method to convert text to speech using ElevenLabs API
        start_time = time.time()
        
        # Construct API endpoint URL with voice ID and audio format parameters
        ELEVENLABS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}?optimize_streaming_latency=3&output_format=pcm_16000"
        
        # Set up request headers with API key and content type
        headers = {
            "xi-api-key": self.ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        
        # Prepare request payload with model settings and voice parameters
        payload = {
            "model_id": "eleven_turbo_v2",  # Specify the TTS model to use
            "text": text,                      # Text to convert to speech
            "voice_settings": {
                "similarity_boost": 1,         # Voice similarity parameter (1 = maximum)
                "stability": 1                 # Voice stability parameter (1 = maximum)
            }
        }

        try:
            # Create an HTTP session for the API request
            async with aiohttp.ClientSession() as session:
                # Send POST request to ElevenLabs API with 10-second timeout
                async with session.post(ELEVENLABS_URL, headers=headers, json=payload, timeout=10) as response:
                    if response.status == 200:
                        # If request successful, read audio content
                        audio_content = await response.read()
                        # Calculate duration of the generated audio
                        duration = self.calculate_audio_duration(audio_content)
                        # Return audio content and its duration
                        return audio_content, duration
                    else:
                        # Handle API error responses
                        error_content = await response.text()
                        # Log error status
                        print(f"{datetime.now()} - ElevenLabs API error: Status {response.status}")
                        # Log error content
                        print(f"{datetime.now()} - Error content: {error_content}")
                        try:
                            # Attempt to parse and log detailed error information
                            error_json = json.loads(error_content)
                            print(f"{datetime.now()} - Error details: {json.dumps(error_json, indent=2)}")
                        except json.JSONDecodeError:
                            # Log if error content isn't valid JSON
                            print(f"{datetime.now()} - Could not parse error content as JSON")
                        # Return None and 0 duration on error
                        return None, 0
                        
        except Exception as e:
            # Handle any other unexpected errors
            print(f"{datetime.now()} - Unexpected error during ElevenLabs API request: {str(e)}")
            print(f"{datetime.now()} - Error type: {type(e).__name__}")
            print(f"{datetime.now()} - Error details:\n{traceback.format_exc()}")
            # Return None and 0 duration if any exception occurs
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

        # Get an available Vonage number
        vonage_number = await vonage_number_manager.get_available_number()
        print(f"Using Vonage number: {vonage_number} for call_id: {call_id}")

        # Store the number with the call for later release
        r.hset(f"{call_id}_metadata", "vonage_number", vonage_number)

        # Create a dynamic configuration
        dynamic_config = {
            "client_name": call_request.client_name,
            "interviewee_name": call_request.interviewee_name,
            "interviewee_last_name": call_request.interviewee_last_name,
            "interviewee_email": call_request.interviewee_email,
            "interviewee_number": call_request.interviewee_number,
            "client_company_description": call_request.client_company_description,
            "agent_name": call_request.agent_name,
            "voice_id": call_request.voice_id,
            "unique_customer_identifier": call_request.unique_customer_identifier,
            "use_case": call_request.use_case,
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
        print(f"Vonage Number in use: {vonage_number}")  # Add this line to log which number is being used
        
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
            'to': [{'type': 'phone', 'number': call_request.interviewee_number}], # Use interviewee_number from the request
            'from': {'type': 'phone', 'number': vonage_number},
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
                                'caller-id': vonage_number
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
            # Skip if we've already processed this call completion
            if call_id in processed_call_completions:
                print(f"{datetime.now()}: Already processed completion for call_id: {call_id}")
                return {"message": "Already processed"}

            # Mark this call as processed
            processed_call_completions.add(call_id)
            
            if call_id in call_instances:
                try:
                    print(f"{datetime.now()}: Starting termination for call_id: {call_id}")

                    # Get instances from call_instances
                    state_machine = call_instances[call_id]["state_machine"]
                    shared_data = call_instances[call_id]["shared_data"]

                    # Set the call_completed flag to True
                    shared_data.call_completed = True

                    # Delay the execution by 2 seconds
                    await asyncio.sleep(120)

                    # Get and release the Vonage number used for this call
                    vonage_number = r.hget(f"{call_id}_metadata", "vonage_number")
                    if vonage_number:
                        vonage_number = vonage_number.decode('utf-8')
                        await vonage_number_manager.release_number(vonage_number)
                        r.delete(f"{call_id}_metadata")
                        print(f"{datetime.now()}: Released Vonage number {vonage_number} for call_id: {call_id}")

                    # Print conversation history before deleting
                    conversation_history = r.get(f'{call_id}_conversation_history')
                    if conversation_history:
                        print(f"Conversation history for call_id {call_id}:")
                        print(json.loads(conversation_history.decode('utf-8')))
                    else:
                        print(f"No conversation history found for call_id {call_id}")

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
                    r.delete(f"{call_id}_metadata")
                    r.delete(f'{call_id}_recording_processing')
                    print(f"{datetime.now()}: Redis history deleted for call_id: {call_id}")

                    print(f"Call terminated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} for call_id: {call_id}")

                except Exception as e:
                    print(f"{datetime.now()}: Error during call termination for call_id: {call_id}: {e}")
                    print(traceback.format_exc())
                    # Remove from processed set if handling failed
                    processed_call_completions.discard(call_id)
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
        response = supabase.table('interviews').insert(interview_data).execute()
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
            # Use Redis SETNX (Set if Not eXists) to implement a lock
            # Returns 1 if key was set (first attempt), 0 if key already exists
            lock_acquired = r.setnx(f'{call_id}_recording_processing', 'true')
            
            if lock_acquired:
                print(f"Call Recording and Post Analysis Starting - call_id: {call_id}")
            else:
                print(f"Second Endpoint Hit on vonage_recording - ignored: {call_id}")
                return {"message": "Recording already being processed"}

            if call_id not in call_instances:
                raise Exception(f"No call instance found for call_id: {call_id}")

            shared_data = call_instances[call_id]["shared_data"]
            sales_gpt_api = call_instances[call_id]["sales_gpt_api"]

            # Run post-call analysis
            print(f"Running post-call analysis for call_id: {call_id}")
            analysis_results = await sales_gpt_api.run_post_call_analysis()
            
            # Retrieve additional data
            dynamic_config = sales_gpt_api.config
            interviewee_name = dynamic_config.get('interviewee_name', '')
            interviewee_last_name = dynamic_config.get('interviewee_last_name', '')
            interviewee_email = dynamic_config.get('interviewee_email', '')
            interviewee_number = dynamic_config.get('interviewee_number', '')
            client_name = dynamic_config.get('client_name', 'Default')
            client_company_description = dynamic_config.get('client_company_description', '')
            agent_name = dynamic_config.get('agent_name', '')
            voice_id = dynamic_config.get('voice_id', '')
            unique_customer_identifier = dynamic_config.get('unique_customer_identifier', '')
            use_case = dynamic_config.get('use_case', '')

            # Get conversation history from Redis
            conversation_history_str = r.get(f'{call_id}_conversation_history')
            if conversation_history_str:
                # Parse the JSON array
                conversation_history = json.loads(conversation_history_str.decode("utf-8"))
                # Clean and join the array elements without quotes and commas
                formatted_history = ''.join(clean_transcript_delimiters(msg) for msg in conversation_history)
            else:
                formatted_history = ''

            print(f"Raw conversation history for call_id {call_id}: {formatted_history}")

            
            # Calculate overall elapsed time
            interview_start_time = sales_gpt_api.sales_agent.interview_start_time
            if interview_start_time is None:
                print(f"Warning: interview_start_time is None for call_id {call_id}")
                interview_start_time = time.time()
                overall_elapsed_time = 0
            else:
                overall_elapsed_time = max(0, (time.time() - interview_start_time) - 60)

            # Calculate interview end time
            interview_end_time = datetime.now().isoformat()

            # Download the recording from Vonage
            vonage_client = VonageClient(
                application_id=VONAGE_APPLICATION_ID,
                private_key=VONAGE_APPLICATION_PRIVATE_KEY_PATH,
            )
            voice = Voice(vonage_client)

            recording_bytes = voice.get_recording(recording_url)

            # Upload the recording to Supabase
            file_path = f'{client_name}/{call_id}.mp3'
            upload_response = supabase.storage.from_('interview_audio_files').upload(file_path, recording_bytes, {
                "Content-Type": "audio/mpeg"
            })
            if upload_response.status_code != 200:
                raise Exception(f"Failed to upload recording for call_id {call_id}: {upload_response.text}")

            # Construct the Supabase URL for the uploaded file
            supabase_url = f"https://sajeudumjrauymwpbidt.supabase.co/storage/v1/object/public/interview_audio_files/{file_path}"
            
            # Save the Supabase URL to the shared_data instance
            shared_data.recording_url = supabase_url
            print(f"Supabase URL for call_id {call_id}: {supabase_url}")

            # Prepare interview data
            interview_data = {
                "user_id": unique_customer_identifier,
                "call_id": call_id,
                "interviewee_first_name": interviewee_name,
                "interviewee_last_name": interviewee_last_name,
                "interviewee_email": interviewee_email,
                "interviewee_number": interviewee_number,
                "client_name": client_name,
                "date_completed": datetime.now().isoformat(),
                "interview_start_time": datetime.fromtimestamp(interview_start_time).isoformat(),
                "interview_end_time": interview_end_time,
                "total_interview_minutes": round(overall_elapsed_time / 60),
                "conversation_history_raw": formatted_history,  # Store as formatted string instead of JSON
                "interview_audio_link": supabase_url,
                "client_company_description": client_company_description,
                "agent_name": agent_name,
                "voice_id": voice_id,
                "unique_customer_identifier": unique_customer_identifier,
                "use_case": use_case,
                
                # Add analysis results
                "analysis_output": analysis_results.get("analysis_output", ""),
                "analysis_part01": analysis_results.get("part01_result", ""),
                "analysis_part02": analysis_results.get("part02_result", ""),
                "analysis_part03": analysis_results.get("part03_result", ""),
                "analysis_part04": analysis_results.get("part04_result", ""),
                "analysis_part05": analysis_results.get("part05_result", ""),
                "analysis_part06": analysis_results.get("part06_result", ""),
            }

            # Save interview data to Supabase
            await save_interview_data(supabase, interview_data)
            
            print(f"Recording URL, interview data, and analysis results saved to Supabase successfully for call_id {call_id}")
            
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
    # Get the sales API instance and agent name for this call
    sales_gpt_api = call_instances[call_id]["sales_gpt_api"]
    agent_name = sales_gpt_api.agent_name.lower()  # Convert to lowercase for consistency
    
    # Map agent name to audio file name
    audio_file_name = f"{agent_name}_voice.raw"
    
    # Specify the exact file path
    audio_folder_path = "/mnt/buffer_audio"
    audio_file_path = os.path.join(audio_folder_path, audio_file_name)

# LOCAL
# async def play_audio_file(websocket: WebSocket, call_id: str, shared_data: SharedData):
#     # Get the sales API instance and agent name for this call
#     sales_gpt_api = call_instances[call_id]["sales_gpt_api"]
#     agent_name = sales_gpt_api.agent_name.lower()  # Convert to lowercase for consistency
    
#     # Map agent name to audio file name
#     audio_file_name = f"{agent_name}_voice.raw"

#     audio_folder_path = r"C:\Users\fletc\Desktop\Franko - 06\SalesGPT\buffer_audio"
#     audio_file_path = os.path.join(audio_folder_path, audio_file_name)
    
    
    chunk_size = 320 * 2

    try:
        print(f"[{datetime.now()}] - Queueing Audio Buffer File Begun for call_id {call_id}: {audio_file_path}")
        
        # Let's try to match the format used in send_audio function
        samples = bytearray()
        
        # Read the entire file first
        async with aiofiles.open(audio_file_path, 'rb') as f:
            samples.extend(await f.read())
            
        print(f"Total audio file size: {len(samples)} bytes")
        
        # Process chunks similar to send_audio function
        while len(samples) >= chunk_size:
            chunk = samples[:chunk_size]
            samples = samples[chunk_size:]
            
            # Send directly to audio queue without batching
            await shared_data.audio_queue.enqueue(chunk)
            
            # Add a small delay between chunks
            await asyncio.sleep(0.01)

        # Handle any remaining samples
        if samples:
            padding_size = chunk_size - len(samples)
            padded_chunk = samples + bytearray(padding_size)
            await shared_data.audio_queue.enqueue(padded_chunk)
            print(f"Added final padded chunk of size: {len(padded_chunk)}")
        else:
            print("No remaining samples to pad")

        print(f"[{datetime.now()}] - Audio buffer file queued successfully")
        shared_data.audio_sending_completed.set()
        
    except FileNotFoundError:
        print(f"Error: Audio file not found at {audio_file_path} for call_id {call_id}")
    except Exception as e:
        print(f"Error playing audio file for call_id {call_id}: {e}")
        print(traceback.format_exc())

# async def generate_and_send_speech(websocket: WebSocket, call_id: str, conversation_history: list, human_response: str, agent_response: str, shared_data: SharedData):
#     try:
#         # Record the start time for timing calculations
#         start_time = time.time()
#         # Log the beginning of speech generation
#         print(f"{datetime.now()} Generate and Send Speech Begun for call_id: {call_id}")
        
#         # Initialize empty dictionary to store results from the language model
#         results = {}
#         # Flag to track if empathy statement has been processed
#         empathy_statement_processed = False
        
#         # Get the sales API instance and voice_id for this call
#         sales_gpt_api = call_instances[call_id]["sales_gpt_api"]
#         voice_id = sales_gpt_api.voice_id
        
#         # Create text-to-speech instance with the configured voice_id
#         tts = TextToSpeech(voice_id=voice_id)

#         # Check if this is the first turn in the conversation
#         is_first_turn = len(conversation_history) == 0

#         # Set duration for buffer audio file (5.2s if not first turn, 0 if first turn)
#         play_audio_file_duration = 5.2 if not is_first_turn else 0  # seconds
#         # Initialize duration trackers for different audio components

#         # Clear any existing audio in the queue
#         if hasattr(shared_data.audio_queue, 'clear'):
#             await shared_data.audio_queue.clear()

#         empathy_duration = 0
#         sales_utterance_duration = 0

#         # Play buffer audio file if not the first turn
#         if not is_first_turn:
#             asyncio.create_task(play_audio_file(websocket, call_id, shared_data))
#         else:
#             play_audio_file_duration = 0
        
#         # Get the sales API instance for this call
#         sales_gpt_api = call_instances[call_id]["sales_gpt_api"]

async def generate_and_send_speech(websocket: WebSocket, call_id: str, conversation_history: list, human_response: str, agent_response: str, shared_data: SharedData):
    try:
        start_time = time.time()
        print(f"{datetime.now()} Generate and Send Speech Begun for call_id: {call_id}")
        
        # Initialize results and flags
        results = {}
        empathy_statement_processed = False
        
        # Get the sales API instance and configuration
        sales_gpt_api = call_instances[call_id]["sales_gpt_api"]
        sales_gpt = call_instances[call_id]["sales_gpt"]  # Get the actual SalesGPT instance
        voice_id = sales_gpt_api.voice_id
        current_category = sales_gpt.get_current_stage_category().lower()
        
        # Create text-to-speech instance
        tts = TextToSpeech(voice_id=voice_id)

        # Check if this is the first turn
        is_first_turn = len(conversation_history) == 0

        # Clear existing audio queue
        if hasattr(shared_data.audio_queue, 'clear'):
            await shared_data.audio_queue.clear()

        # Initialize duration trackers
        empathy_duration = 0
        sales_utterance_duration = 0
        play_audio_file_duration = 0  # Default to 0

        # Determine if buffer audio should play based on category
        if not is_first_turn and current_category == "exploratory":
            print(f"{datetime.now()} Playing buffer audio for exploratory category, call_id: {call_id}")
            asyncio.create_task(play_audio_file(websocket, call_id, shared_data))
            play_audio_file_duration = 5.2  # Set duration after deciding to play
        else:
            print(f"{datetime.now()} Skipping buffer audio for category: {current_category}, call_id: {call_id}")

        
        # Process each partial result from the language model
        async for partial_result in sales_gpt_api.run_chains(conversation_history, human_response, agent_response):
            # Update results dictionary with new partial results
            results.update(partial_result)
            
            # Process empathy statement if present and not already processed
            if not is_first_turn and "empathy_statement" in partial_result and not empathy_statement_processed:
                print(f"{datetime.now()} Empathy Statement Audio Generation Begun for call_id: {call_id}")
                
            #     # Generate audio for empathy statement
            #     empathy_audio_data, empathy_duration = await tts.generate_speech(results["empathy_statement"])
            #     print(f"{datetime.now()} Empathy Statement Audio Generation Returned for call_id: {call_id}")
                
            #     # Queue the empathy statement audio for sending
            #     await send_audio(websocket, empathy_audio_data, empathy_duration, call_id, shared_data)
            #     print(f"{datetime.now()} Empathy Statement Audio Queued for call_id: {call_id}")

                async def process_empathy_audio():
                    try:
                        audio_data, duration = await tts.generate_speech(results["empathy_statement"])
                        print(f"{datetime.now()} Empathy TTS completed, queueing audio for call_id: {call_id}")
                        await send_audio(websocket, audio_data, duration, call_id, shared_data)
                    except Exception as e:
                        print(f"Error in empathy audio processing for call_id {call_id}: {e}")
                
                asyncio.create_task(process_empathy_audio())
                empathy_statement_processed = True
                
                # Mark empathy statement as processed
                empathy_statement_processed = True

        # Generate the main response from the sales agent
        print(f"{datetime.now()} Lead Interviewer Statement Generation Begun for call_id: {call_id}")
        sales_utterance_response = await sales_gpt_api.do(
            conversation_history,
            human_response,
            empathy_statement=results.get("empathy_statement", ""),
            current_goal_review_narrative=results.get("current_goal_review_narrative", ""),
            current_goal_review_outcome=results.get("current_goal_review_outcome", ""),
            current_goal_review_product=results.get("current_goal_review_product", "")
        )
        # Log the full response for debugging
        print(f"[sales_gpt_api.do output] Full response:\n{sales_utterance_response}")
        # Extract the relevant part of the response
        extracted_response = extract_desired_response(sales_utterance_response)
        print(f"{datetime.now()} Lead Interviewer Statement Generation Returned for call_id: {call_id}")

        # Generate audio for the main response
        sales_utterance_audio_data, sales_utterance_duration = await tts.generate_speech(extracted_response)
        print(f"{datetime.now()} Lead Interviewer Audio Generation Returned for call_id: {call_id}")

        # Queue the main response audio for sending
        print(f"{datetime.now()} Lead Interviewer Audio to Queue Begun for call_id: {call_id}")
        await send_audio(websocket, sales_utterance_audio_data, sales_utterance_duration, call_id, shared_data)
        print(f"{datetime.now()} Lead Interviewer Audio to Queue Returned for call_id: {call_id}")

        # Wait until all queued audio has been sent
        while not await shared_data.audio_queue.is_empty():
            await asyncio.sleep(0.1)

        # Clear the audio queue after all audio has been sent
        await shared_data.audio_queue.clear()
        print(f"{datetime.now()} Audio queue cleared for call_id: {call_id}")

        # Calculate timing metrics
        end_time = time.time()
        elapsed_time = end_time - start_time
        # Total duration of all audio components
        audio_playback_time = play_audio_file_duration + empathy_duration + sales_utterance_duration
        # Calculate delay needed to ensure proper audio timing
        audio_state_delay = max(0, audio_playback_time - elapsed_time)

        # Log timing information
        print(f"{datetime.now()} Generate and Send Speech Returned for call_id: {call_id}")
        print(f"Elapsed time: {elapsed_time:.2f}s, Audio playback time: {audio_playback_time:.2f}s, Audio state delay: {audio_state_delay:.2f}s")

        # Return the empathy statement, extracted response, and calculated delay
        return results.get("empathy_statement", ""), extracted_response, audio_state_delay, audio_playback_time

    except Exception as e:
        print(f"Error in generate_and_send_speech for call_id {call_id}: {e}")
        print(f"Error in generate_and_send_speech: {type(e).__name__}: {str(e)}")
        print(traceback.format_exc())
        # Return default values in case of error, maintaining the same structure as the success case
        return "", "", 0, 0



def extract_desired_response(response):
    print(f"[extract_desired_response input] Full text received:\n{response}")

    start_marker = "<!-- START_OF_RESPONSE -->"
    end_marker = "<!-- END_OF_RESPONSE -->"
    
    start = response.find(start_marker) 
    print(f"Start marker position: {start}")
    
    if start != -1:
        # Look for the end marker after the start marker
        end = response.find(end_marker, start + len(start_marker))
        
        if end != -1:
            # Extract the content between the markers
            extracted = response[start + len(start_marker):end].strip()
        else:
            print("Could not find end marker, returning everything after start marker")
            # If end marker is not found, return everything after the start marker
            extracted = response[start + len(start_marker):].strip()
    else:
        print("Could not find start marker")
        # If the start marker is not found, return the original response
        extracted = response.strip()

    # Print selected response after it's been extracted
    print("\n=== Selected Lead Response ===")
    print(f"{extracted}\n")
    print("=======================\n")
    
    return extracted



# # With lock
# async def send_audio(vonage_websocket: WebSocket, audio_data, duration, call_id: str, shared_data: SharedData):
#     try:
#         # Acquire lock before starting new audio segment
#         async with shared_data.audio_lock:
#             print(f"{datetime.now()} Queueing Audio Stream - Begun for call_id: {call_id}")
            
#             if not audio_data:
#                 print(f"{datetime.now()} Warning: Empty audio data received for call_id: {call_id}")
#                 return
                
#             # Reset completion flag before starting new audio
#             shared_data.audio_sending_completed.clear()
            
#             samples = bytearray(audio_data)
#             chunk_size = 320 * 2  # 20ms of audio at 16kHz, 16-bit
            
#             # Process full chunks
#             while len(samples) >= chunk_size:
#                 chunk = samples[:chunk_size]
#                 samples = samples[chunk_size:]
#                 await shared_data.audio_queue.enqueue(chunk)

#             # Handle remaining samples with padding
#             if samples:
#                 padding_size = chunk_size - len(samples)
#                 padded_chunk = samples + bytearray(padding_size)
#                 await shared_data.audio_queue.enqueue(padded_chunk)

#             print(f"{datetime.now()} Queueing Audio Stream - Finished for call_id: {call_id}")
#             shared_data.audio_sending_completed.set()

#             # Wait for current audio to finish before releasing lock
#             while not await shared_data.audio_queue.is_empty():
#                 await asyncio.sleep(0.1)

#     except Exception as e:
#         print(f"{datetime.now()} Error in send_audio: {e}")
#         print(traceback.format_exc())


# async def send_queued_audio(vonage_websocket: WebSocket, shared_data: SharedData):
#     chunk_size = 320 * 2  # 20ms of audio at 16kHz, 16-bit
#     chunk_duration = 0.02  # 20ms per chunk
#     initial_buffer_duration = 1.5   # Buffer 0.5 seconds of audio
#     initial_buffer_chunks = int(initial_buffer_duration / chunk_duration)
#     buffer = []
#     buffering_timeout = 3.0
#     buffering_start_time = time.time()

#     try:
#         while not shared_data.call_completed:
#             # Reset buffer for new audio segment
#             buffer = []
#             buffering_start_time = time.time()

#             # Accumulate initial buffer
#             print(f"{datetime.now()} Starting initial buffer accumulation...")
#             while len(buffer) < initial_buffer_chunks:
#                 audio_chunk = await shared_data.audio_queue.dequeue()
#                 if audio_chunk is not None:
#                     buffer.append(audio_chunk)
#                 else:
#                     if time.time() - buffering_start_time > buffering_timeout:
#                         if not buffer:  # If buffer is empty, wait for next audio
#                             await asyncio.sleep(0.1)
#                             break
#                         print(f"{datetime.now()} Buffering timeout reached with {len(buffer)} chunks")
#                         break
#                     await asyncio.sleep(0.001)

#             if buffer:  # Only process if we have audio to send
#                 print(f"{datetime.now()} Initial buffer accumulated with {len(buffer)} chunks")

#                 # Record the start time
#                 start_time = time.time()
#                 next_send_time = start_time

#                 # Send the initial buffer
#                 for chunk in buffer:
#                     if vonage_websocket.client_state == WebSocketState.DISCONNECTED:
#                         print(f"{datetime.now()} WebSocket disconnected during initial buffer send")
#                         return
#                     await vonage_websocket.send_bytes(chunk)
#                     next_send_time += chunk_duration

#                 buffer.clear()

#                 # Continue sending audio chunks in real-time
#                 while True:
#                     audio_chunk = await shared_data.audio_queue.dequeue()
#                     if audio_chunk is not None:
#                         now = time.time()
#                         sleep_time = next_send_time - now

#                         if sleep_time > 0:
#                             await asyncio.sleep(sleep_time)

#                         if vonage_websocket.client_state == WebSocketState.DISCONNECTED:
#                             print(f"{datetime.now()} WebSocket disconnected during streaming")
#                             return

#                         await vonage_websocket.send_bytes(audio_chunk)
#                         next_send_time += chunk_duration
#                     else:
#                         if shared_data.audio_sending_completed.is_set() and await shared_data.audio_queue.is_empty():
#                             print(f"{datetime.now()} Audio segment completed")
#                             break  # Break inner loop to start new segment
#                         await asyncio.sleep(0.001)

#     except WebSocketDisconnect:
#         print(f"{datetime.now()} WebSocket disconnected")
#     except Exception as e:
#         print(f"{datetime.now()} Error in send_queued_audio: {e}")
#         print(traceback.format_exc())


async def send_audio(vonage_websocket: WebSocket, audio_data, duration, call_id: str, shared_data: SharedData):
    try:
        async with shared_data.audio_lock:
            print(f"{datetime.now()} Queueing Audio Stream - Begun for call_id: {call_id}")
            
            if not audio_data:
                print(f"{datetime.now()} Warning: Empty audio data received for call_id: {call_id}")
                return
                
            # Reset completion flag before starting new audio
            shared_data.audio_sending_completed.clear()
            
            samples = bytearray(audio_data)
            chunk_size = 320 * 2  # 20ms of audio at 16kHz, 16-bit
            
            # Process full chunks
            while len(samples) >= chunk_size:
                chunk = samples[:chunk_size]
                samples = samples[chunk_size:]
                await shared_data.audio_queue.enqueue(chunk)

            # Handle remaining samples with padding
            if samples:
                padding_size = chunk_size - len(samples)
                padded_chunk = samples + bytearray(padding_size)
                await shared_data.audio_queue.enqueue(padded_chunk)

            print(f"{datetime.now()} Queueing Audio Stream - Finished for call_id: {call_id}")
            
            # Move this after all chunks are queued
            shared_data.audio_sending_completed.set()

            # Remove this wait - it's causing premature lock release
            # while not await shared_data.audio_queue.is_empty():
            #     await asyncio.sleep(0.1)

    except Exception as e:
        print(f"{datetime.now()} Error in send_audio: {e}")
        print(traceback.format_exc())

async def send_queued_audio(vonage_websocket: WebSocket, shared_data: SharedData):
    chunk_size = 320 * 2  # 20ms of audio at 16kHz, 16-bit
    chunk_duration = 0.02  # 20ms per chunk
    initial_buffer_duration = 1.5   # Buffer 1.5 seconds of audio
    initial_buffer_chunks = int(initial_buffer_duration / chunk_duration)
    buffer = []
    buffering_timeout = 3.0
    last_chunk_time = None

    try:
        while not shared_data.call_completed:
            buffer = []
            buffering_start_time = time.time()
            last_chunk_time = None  # Reset timing for new segment

            # Accumulate initial buffer
            print(f"{datetime.now()} Starting initial buffer accumulation...")
            while len(buffer) < initial_buffer_chunks:
                audio_chunk = await shared_data.audio_queue.dequeue()
                if audio_chunk is not None:
                    buffer.append(audio_chunk)
                    last_chunk_time = time.time()  # Track last received chunk
                else:
                    if time.time() - buffering_start_time > buffering_timeout:
                        if not buffer:
                            await asyncio.sleep(0.1)
                            break
                        print(f"{datetime.now()} Buffering timeout reached with {len(buffer)} chunks")
                        break
                    await asyncio.sleep(0.001)

            if buffer:
                print(f"{datetime.now()} Initial buffer accumulated with {len(buffer)} chunks")
                start_time = time.time()
                next_send_time = start_time

                # Send initial buffer
                for chunk in buffer:
                    if vonage_websocket.client_state == WebSocketState.DISCONNECTED:
                        print(f"{datetime.now()} WebSocket disconnected during initial buffer send")
                        return
                    await vonage_websocket.send_bytes(chunk)
                    next_send_time += chunk_duration

                buffer.clear()

                # Continue sending audio chunks in real-time
                while True:
                    audio_chunk = await shared_data.audio_queue.dequeue()
                    if audio_chunk is not None:
                        last_chunk_time = time.time()
                        now = time.time()
                        sleep_time = next_send_time - now

                        if sleep_time > 0:
                            await asyncio.sleep(sleep_time)

                        if vonage_websocket.client_state == WebSocketState.DISCONNECTED:
                            print(f"{datetime.now()} WebSocket disconnected during streaming")
                            return

                        await vonage_websocket.send_bytes(audio_chunk)
                        next_send_time += chunk_duration
                    else:
                        # Wait longer before breaking to ensure all audio is played
                        if shared_data.audio_sending_completed.is_set():
                            if last_chunk_time and time.time() - last_chunk_time > 0.2:  # Wait 500ms after last chunk
                                print(f"{datetime.now()} Audio segment completed")
                                break
                        await asyncio.sleep(0.001)

    except WebSocketDisconnect:
        print(f"{datetime.now()} WebSocket disconnected")
    except Exception as e:
        print(f"{datetime.now()} Error in send_queued_audio: {e}")
        print(traceback.format_exc())




# Define send_to_assembly
async def send_to_assembly(assembly_ws, vonage_ws, shared_data, call_id):
    """Send audio data from the Vonage WebSocket to the AssemblyAI WebSocket."""
    while True:
        try:
            # Wait for incoming WebSocket messages from Vonage
            message_data = await vonage_ws.receive()
            if message_data.get("type") == "websocket.receive" and "bytes" in message_data:
                # Get the audio data from the message
                audio_data = message_data["bytes"]
                # Add it to the buffer
                shared_data.audio_buffer.extend(audio_data)

                # When we have enough data (~100ms of audio at 16kHz, 16kHz * 2 bytes/sample * 0.1s = 3200 bytes)
                if len(shared_data.audio_buffer) >= 3200:
                    # Encode the audio data in base64
                    data = base64.b64encode(shared_data.audio_buffer).decode("utf-8")
                    # Create the JSON payload
                    json_data = json.dumps({"audio_data": data})
                    # Send to AssemblyAI
                    await assembly_ws.send(json_data)
                    # Clear the buffer
                    shared_data.audio_buffer = bytearray()
            else:
                # Log non-audio messages
                # print(f"{datetime.now()}: Received non-bytes message in send_to_assembly for call_id {call_id}: {message_data}")
                pass
        except Exception as e:
            # Log any errors and break the loop
            print(f"{datetime.now()}: Error in send_to_assembly for call_id {call_id}: {e}")
            print(traceback.format_exc())
            break

# Define receive_from_assembly
async def receive_from_assembly(assembly_ws, shared_data, call_id):
    """Receive transcriptions from AssemblyAI WebSocket and handle them."""
    while True:
        try:
            # Wait for messages from AssemblyAI
            result_str = await assembly_ws.recv()
            # print(f"{datetime.now()}: Received message from AssemblyAI for call_id {call_id}: {result_str}")
            result = json.loads(result_str)
            if 'text' in result:
                # Update timestamps based on whether text was received
                if result['text'].strip():
                    shared_data.update_word_timestamp()
                else:
                    shared_data.update_no_word_timestamp()

                # Handle different types of transcripts
                if result['message_type'] == 'FinalTranscript' and result['text'].strip():
                    # Save final transcripts
                    shared_data.add_part(result['text'])
                    print(f"{datetime.now()}: Appending final transcript - {result['text']}")
                elif result['message_type'] == 'PartialTranscript' and result['text'].strip():
                    # Log partial transcripts
                    print(f"{datetime.now()}: Partial transcript - {result['text']}")
        except Exception as e:
            # Log any errors and break the loop
            print(f"{datetime.now()}: Error in receive_from_assembly for call_id {call_id}: {e}")
            print(traceback.format_exc())
            break



class WebSocketManager:
    def __init__(self, websocket: WebSocket, shared_data: SharedData):
        # Store the WebSocket connection instance
        self.websocket = websocket
        # Store the shared data instance that contains call-related information
        self.shared_data = shared_data
        # Store the call ID from shared data for tracking purposes
        self.call_id = shared_data.call_id
        # Initialize counter for reconnection attempts
        self.reconnect_attempts = 0
        # Set maximum number of reconnection attempts allowed
        self.max_reconnect_attempts = 5
        # Set initial delay between reconnection attempts (in seconds)
        self.reconnect_delay = 1
        # Flag to track if a reconnection is currently in progress
        self.is_reconnecting = False

    async def connect(self):
        # Accept the incoming WebSocket connection
        await self.websocket.accept()
        # Store the WebSocket instance in shared data
        self.shared_data.set_websocket(self.websocket)
        # Signal that the WebSocket is ready for use
        self.shared_data.websocket_ready.set()
        # Log successful connection
        print(f"WebSocket connection accepted for call_id: {self.call_id}")

    async def disconnect(self):
        # Close the WebSocket connection
        await self.websocket.close()
        # Log disconnection
        print("WebSocket disconnected.")

    async def send_message(self, message: dict):
        # Send a JSON message through the WebSocket
        await self.websocket.send_json(message)

    async def receive_message(self):
        try:
            # Receive a message from the WebSocket
            message = await self.websocket.receive()
            # Handle different message types
            if message["type"] == "websocket.receive":
                return message
            elif message["type"] == "websocket.disconnect":
                # Raise disconnect exception if connection is closed
                raise WebSocketDisconnect(message["code"], message["reason"])
            else:
                # Raise error for unexpected message types
                raise ValueError(f"Unexpected message type: {message['type']}")
        except WebSocketDisconnect as e:
            # Log disconnect error and re-raise the exception
            print(f"Error in WebSocket connection for call_id {self.call_id}: {e}")
            raise

    async def reconnect(self):
        # Prevent multiple simultaneous reconnection attempts
        if self.is_reconnecting:
            return

        # Set reconnection flag and reset attempt counter
        self.is_reconnecting = True
        self.reconnect_attempts = 0

        # Try to reconnect until max attempts reached
        while self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                # Increment attempt counter
                self.reconnect_attempts += 1
                print(f"Attempting to reconnect WebSocket (Attempt {self.reconnect_attempts})...")

                # Create a new WebSocket connection
                new_websocket = await WebSocket.connect(self.websocket.url)

                # Update shared data with new connection
                self.shared_data.set_websocket(new_websocket)

                # Update manager's WebSocket instance
                self.websocket = new_websocket

                # Log successful reconnection
                print("WebSocket reconnected successfully.")
                self.is_reconnecting = False
                return

            except Exception as e:
                # Log reconnection failure
                print(f"Failed to reconnect WebSocket: {e}")
                # Wait before next attempt with exponential backoff
                await asyncio.sleep(self.reconnect_delay)
                # Double the delay for next attempt
                self.reconnect_delay *= 2

        # Log failure after max attempts reached
        print("Max reconnect attempts reached. WebSocket reconnection failed.")
        self.is_reconnecting = False

    async def should_reconnect(self):
        # Determine if reconnection should be attempted based on call status
        return not self.shared_data.call_completed

class WebSocketConnectionManager:
    def __init__(self, ws):
        self.ws = ws
        self.is_connected = True

    async def send_safely(self, data):
        """Send data through websocket with error handling"""
        try:
            if self.is_connected:
                await self.ws.send(data)
                return True
        except websockets.exceptions.ConnectionClosedOK:
            self.is_connected = False
            print(f"{datetime.now()}: WebSocket connection closed normally")
        except Exception as e:
            self.is_connected = False
            print(f"{datetime.now()}: Error sending data: {e}")
        return False

    async def receive_safely(self):
        """Receive data from websocket with error handling"""
        try:
            if self.is_connected:
                return await self.ws.recv()
        except websockets.exceptions.ConnectionClosedOK:
            self.is_connected = False
            print(f"{datetime.now()}: WebSocket connection closed normally")
        except Exception as e:
            self.is_connected = False
            print(f"{datetime.now()}: Error receiving data: {e}")
        return None

    async def close(self):
        """Close the websocket connection safely"""
        try:
            if self.is_connected:
                await self.ws.close()
                self.is_connected = False
        except Exception as e:
            print(f"{datetime.now()}: Error closing WebSocket: {e}")
            print(traceback.format_exc())

    def is_active(self):
        """Check if the connection is still active"""
        return self.is_connected


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, call_id: str = Query(...)):
    # Log the opening of the WebSocket connection
    print(f"{datetime.now()}: WebSocket connection opened for call_id: {call_id}")

    # Verify that the call_id exists in our tracking system
    if call_id not in call_instances:
        print(f"{datetime.now()}: Error: No call instance found for call_id: {call_id}")
        await websocket.close(code=1000)
        return

    # Get the shared data instance for this call
    shared_data = call_instances[call_id]["shared_data"]
    # Create a WebSocket manager instance
    websocket_manager = WebSocketManager(websocket, shared_data)
    # Establish the WebSocket connection
    await websocket_manager.connect()

    # Create a background task for sending queued audio
    audio_send_task = asyncio.create_task(send_queued_audio(websocket_manager.websocket, shared_data))

    # Set up AssemblyAI connection details
    URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"

    # Get the API key from environment variables
    auth_key = os.environ.get("ASSEMBLYAI_API_KEY")

    # Verify API key exists
    if not auth_key:
        print(f"{datetime.now()}: Error: ASSEMBLYAI_API_KEY is not set in the environment variables.")
        await websocket.close(code=1000)
        return

    # Initialize the audio buffer for collecting audio data
    shared_data.audio_buffer = bytearray()

    # Establish and maintain the AssemblyAI connection
    try:
        # Connect to AssemblyAI with authentication and keepalive settings
        async with websockets.connect(
            URL,
            extra_headers=(("Authorization", auth_key),),
            ping_interval=5,
            ping_timeout=120
        ) as assembly_ws:
            print(f"{datetime.now()}: Connected to AssemblyAI WebSocket for call_id {call_id}")

            # Run send_to_assembly and receive_from_assembly functions concurrently
            send_task = asyncio.create_task(send_to_assembly(assembly_ws, websocket_manager.websocket, shared_data, call_id))
            receive_task = asyncio.create_task(receive_from_assembly(assembly_ws, shared_data, call_id))

            # Await both tasks to run concurrently
            await asyncio.gather(
                send_task,
                receive_task
            )
    except Exception as e:
        # Log any connection errors
        print(f"{datetime.now()}: Exception occurred while connecting to AssemblyAI for call_id {call_id}: {e}")
        print(traceback.format_exc())
    finally:
        # Cleanup section
        # Cancel the audio sending task
        audio_send_task.cancel()
        try:
            await audio_send_task
        except asyncio.CancelledError:
            pass

        # Close the WebSocket connection if it's still open
        try:
            if websocket_manager.websocket.client_state.name != "DISCONNECTED":
                await websocket_manager.disconnect()
                print(f"{datetime.now()}: WebSocket disconnected successfully for call_id: {call_id}")
        except Exception as e:
            print(f"{datetime.now()}: Error closing WebSocket connection for call_id {call_id}: {e}")
            print(traceback.format_exc())

# Add this function near the top with other utility functions
def clean_transcript_delimiters(text):
    """Remove any response delimiters and extraction question tags that might have leaked into the transcript"""
    text = text.replace('<!-- START_OF_RESPONSE -->', '').strip()
    text = text.replace('<!-- END_OF_RESPONSE -->', '').strip()
    text = text.replace('</extraction_question>', '').strip()
    text = text.replace('<extraction_question>', '').strip()
    return text

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)