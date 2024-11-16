# Import required libraries for API functionality, chat models, and utilities
import json
import os
from langchain_community.chat_models import ChatLiteLLM
import asyncio
from salesgpt.agents import SalesGPT
import re
from datetime import datetime

# Model selection - currently set to GPT-4
# Multiple model options are commented out for easy switching
GPT_MODEL = "gpt-4o" 
# GPT_MODEL = "claude-2"
# GPT_MODEL = "claude-3-haiku-20240307"
# GPT_MODEL = "claude-3-opus-20240229"
# GPT_MODEL = "groq/llama3-70b-8192"
# GPT_MODEL = "groq/llama2-70b-4096"
# GPT_MODEL = "groq/mixtral-8x7b-32768"
# GPT_MODEL = "replicate/meta/meta-llama-3-8b-instruct"

# API key declarations - retrieved from environment variables for security
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

class SalesGPTAPI:
    # Initialize the SalesGPT API with configuration and call ID
    def __init__(self, config: dict, call_id: str):
        # Store configuration and call ID
        self.config = config
        self.call_id = call_id
        # Initialize the language model with temperature=1 for creative responses
        self.llm = ChatLiteLLM(temperature=1, model_name=GPT_MODEL)
        self.sales_agent = None
        self.first_turn = True

        # Dynamically set all config values as class attributes
        for key, value in self.config.items():
            setattr(self, key, value)

    # Create and configure a new sales agent instance
    def initialize_agent(self):
        # Initialize SalesGPT agent with necessary parameters
        self.sales_agent = SalesGPT.from_llm(
            self.llm,
            verbose=False,
            call_id=self.call_id,
            client_name=self.client_name,
            interviewee_name=self.interviewee_name,
            interviewee_last_name=self.interviewee_last_name,
            interviewee_email=self.interviewee_email,
            to_number=self.to_number,
        )
        # Prepare the agent with initial context
        self.sales_agent.seed_agent()

    # Record the start time of the interview
    def set_interview_start_time(self):
        self.sales_agent.set_interview_start_time()
        return self.sales_agent

    # Main chain execution method for processing conversation
    async def run_chains(self, conversation_history, human_response, agent_response):
        try:
            print(f"[{datetime.now()}] Run Chains Begun")

            # Update agent's conversation state
            self.sales_agent.conversation_history = conversation_history if isinstance(conversation_history, list) else []
            self.sales_agent.human_response = human_response
            self.sales_agent.agent_response = agent_response
            self.sales_agent.goal_completeness_status = self.sales_agent.goal_completeness_status or "N/A"

            # Get current conversation stage category
            current_category = self.sales_agent.get_current_stage_category().lower()

            # Check if this is the first interaction
            is_first_turn = len(self.sales_agent.conversation_history) == 0

            # Handle empathy statement generation
            empathy_task = None
            if not is_first_turn:
                empathy_task = asyncio.create_task(self.sales_agent.run_empathy_statement_chain())
            
            # Handle main conversation chain
            chain_results_task = None
            if current_category != "verbatim":
                chain_results_task = asyncio.create_task(self.sales_agent.async_chain_runner())

            # Process and yield empathy statement
            if empathy_task:
                empathy_statement = await empathy_task
                self.empathy_statement = empathy_statement
                yield {"empathy_statement": empathy_statement}
            else:
                yield {"empathy_statement": ""}

            # Process and yield chain results
            if chain_results_task:
                chain_results = await chain_results_task
                yield chain_results
            else:
                yield {
                    "current_goal_review_narrative": "",
                    "current_goal_review_outcome": "",
                    "current_goal_review_product": ""
                }

        except Exception as e:
            print(f"Error in run_chains: {e}")
            print(traceback.format_exc())
            raise

    # Update the conversation stage based on current context
    async def update_conversation_stage(self):
        try:
            await self.sales_agent.determine_conversation_stage()
        except AttributeError as e:
            print(f"Caught AttributeError: {e}")
            raise

    # Process a standard non-streaming response
    async def do(self, conversation_history: list, human_input=None, empathy_statement=None, 
                 current_goal_review_narrative=None, current_goal_review_outcome=None, 
                 current_goal_review_product=None):
        ai_log = await self.sales_agent._call({
            "empathy_statement": empathy_statement,
            "current_goal_review_narrative": current_goal_review_narrative,
            "current_goal_review_outcome": current_goal_review_outcome,
            "current_goal_review_product": current_goal_review_product,
        })

        return ai_log["text"]



