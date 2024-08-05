import json
import os
from langchain_community.chat_models import ChatLiteLLM
import asyncio
from salesgpt.agents02 import SalesGPT
import re
from datetime import datetime



# import logging
# logging.getLogger("requests").setLevel(logging.WARNING)
# logging.basicConfig(level=logging.WARNING)  # Set global logging level
# logging.getLogger().setLevel(logging.WARNING)  # Set root logger level

# GPT_MODEL = "gpt-3.5-turbo"
GPT_MODEL = "gpt-4o" 
# GPT_MODEL = "claude-2"
# GPT_MODEL = "claude-3-haiku-20240307"
# GPT_MODEL = "claude-3-opus-20240229"
# GPT_MODEL = "groq/llama3-70b-8192"
# GPT_MODEL = "groq/llama2-70b-4096"
# GPT_MODEL = "groq/mixtral-8x7b-32768"
# GPT_MODEL = "replicate/meta/meta-llama-3-8b-instruct"

# ChatLiteLLM.set_verbose = True

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# This initialises the SalesGPT class
# In my current code, I saved a new instance each time the /call endpoint is hit
# So will need to do that and ensure the config pass in works
# This is seemingly also where the model is decided

# class SalesGPTAPI:
#     def __init__(self, config_path: str, call_id: str, verbose: bool = False):
#         self.config_path = config_path
#         self.call_id = call_id
#         self.verbose = verbose
#         self.llm = ChatLiteLLM(temperature=1, model_name=GPT_MODEL)
#         self.sales_agent = None
#         self.first_turn = True


#     def initialize_agent(self):
#         with open(self.config_path, "r") as f:
#             config = json.load(f)
#         # config['call_id'] = self.call_id
#         self.sales_agent = SalesGPT.from_llm(self.llm, verbose=self.verbose, call_id=self.call_id, **config)
#         self.sales_agent.seed_agent()
#         return self.sales_agent

# class SalesGPTAPI:
#     def __init__(self, config_path: str, call_id: str):
#         self.config_path = config_path
#         self.call_id = call_id
#         self.load_config()
#         self.llm = ChatLiteLLM(temperature=1, model_name=GPT_MODEL)
#         self.sales_agent = None
#         self.first_turn = True

#     def load_config(self):
#         with open(self.config_path, 'r') as f:
#             self.config = json.load(f)
        
#         # Load all config values as attributes
#         for key, value in self.config.items():
#             setattr(self, key, value)

#     def initialize_agent(self):
#         self.sales_agent = SalesGPT.from_llm(
#             self.llm,
#             verbose=False,
#             call_id=self.call_id,
#             client_name=self.client_name,
#             interviewee_name=self.interviewee_name,
#             interviewee_last_name=self.interviewee_last_name,
#             interviewee_email=self.interviewee_email,
#             to_number=self.to_number,
#         )
        
#         # # Print attributes before seeding
#         # print("SalesGPT attributes before seeding:")
#         # for attr, value in self.sales_agent.__dict__.items():
#         #     if not callable(value) and not attr.startswith("__"):
#         #         print(f"{attr}: {value}")

#         self.sales_agent.seed_agent()

class SalesGPTAPI:
    def __init__(self, config: dict, call_id: str):
        self.config = config
        self.call_id = call_id
        self.llm = ChatLiteLLM(temperature=1, model_name=GPT_MODEL)
        self.sales_agent = None
        self.first_turn = True

        # Load all config values as attributes
        for key, value in self.config.items():
            setattr(self, key, value)

    # Remove the load_config method as it's no longer needed

    def initialize_agent(self):
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
        
        self.sales_agent.seed_agent()



    def set_interview_start_time(self):
        self.sales_agent.set_interview_start_time()

        # # Print attributes after seeding
        # print("\nSalesGPT attributes after seeding:")
        # for attr, value in self.sales_agent.__dict__.items():
        #     if not callable(value) and not attr.startswith("__"):
        #         print(f"{attr}: {value}")

        return self.sales_agent

    # Works with test 14
    async def run_chains(self, conversation_history, human_response, agent_response):
        try:
            print(f"[{datetime.now()}] Run Chains Begun")

            self.sales_agent.conversation_history = conversation_history if isinstance(conversation_history, list) else []
            self.sales_agent.human_response = human_response
            self.sales_agent.agent_response = agent_response
            self.sales_agent.goal_completeness_status = self.sales_agent.goal_completeness_status or "N/A"

            if self.first_turn:
                await asyncio.sleep(1)
                yield {
                    "empathy_statement": "Hi there, this is Franko! I'm super excited to chat with you today!",
                    "key_points": "",
                    "current_goal_review": "This is the very turn of the interview conversation. Focus on introducing the interview. Here's an example Lead Interviewer response to get started, \"The purpose of our call will be to discuss your experience with [client_name]. It will be recorded and shared with the team, I know they'll appreciate your insights! The interview will take approximately 45 minutes. Are you in a quiet place and ready to get started?\""
                }
            else:
                # Run both chains concurrently
                empathy_task = asyncio.create_task(self.sales_agent.run_empathy_statement_chain())
                chain_results_task = asyncio.create_task(self.sales_agent.async_chain_runner())

                # Yield empathy statement as soon as it's available
                empathy_statement = await empathy_task
                yield {"empathy_statement": empathy_statement}

                # Wait for the other task to complete
                chain_results = await chain_results_task
                yield chain_results

            self.first_turn = False

        except Exception as e:
            print(f"Error in run_chains: {e}")
            print(traceback.format_exc())
            raise


    async def update_conversation_stage(self):
        try:
            # print(f"Attempting to call determine_conversation_stage on {self.sales_agent}")
            await self.sales_agent.determine_conversation_stage()
        except AttributeError as e:
            print(f"Caught AttributeError: {e}")
            # print(f"sales_agent is currently: {self.sales_agent}, of type: {type(self.sales_agent)}")
            raise

    # This do method essentially just runs the standard non-stream response
    async def do(self, conversation_history: list, human_input=None, empathy_statement=None, key_points=None, current_goal_review=None):
        # print("do() method empathy_statement argument:", empathy_statement)
        # print("SalesGPTAPI.empathy_statement attribute:", getattr(self, "empathy_statement", None))
        # print("SalesGPTAPI.sales_agent.empathy_statement attribute:", getattr(self.sales_agent, "empathy_statement", None))

        ai_log = await self.sales_agent._call({
            "empathy_statement": empathy_statement,
            # "conversation_summary": conversation_summary,
            "key_points": key_points,
            "current_goal_review": current_goal_review,
        })

        return ai_log["text"].rstrip('<END_OF_TURN>')




    # This is probably what I want to use
    # Passes in the conversation history
    # async def do_stream(self, conversation_history: [str], human_input=None):
    #     current_turns = len(conversation_history) + 1
    #     if current_turns >= self.max_num_turns:
    #         print("Maximum number of turns reached - ending the conversation.")
    #         yield ["BOT","In case you'll have any questions - just text me one more time!"]
    #         raise StopAsyncIteration

    #     # Don't think this seed_agent is necessary as already run in the initialisation
    #     self.sales_agent.seed_agent()

    #     # Updates the conversation history
    #     self.sales_agent.conversation_history = conversation_history

    #     # This updates the human input which when I get my main file up and running won't be necessary
    #     if human_input is not None:
    #         self.sales_agent.human_step(human_input)


    #     stream_gen = self.sales_agent.astep(stream=True)
    #     for model_response in stream_gen:
    #         for choice in model_response.choices:
    #             message = choice['delta']['content']
    #             if message is not None:
    #                 print(message)  # Print the message to the terminal
    #                 if "<END_OF_CALL>" in message:
    #                     print("Sales Agent determined it is time to end the conversation.")
    #                     yield ["BOT","In case you'll have any questions - just text me one more time!"]
    #                 yield message
    #             else:
    #                 continue