"""
This is salesgptapi01.py file
"""

import json
import os
from langchain_community.chat_models import ChatLiteLLM
import asyncio
from salesgpt.agents01 import SalesGPT
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

class SalesGPTAPI:
    USE_TOOLS = False

    def __init__(self, config_path: str, verbose: bool = False, max_num_turns: int = 20, use_tools=False):
        self.config_path = config_path
        self.verbose = verbose
        self.max_num_turns = max_num_turns
        # self.llm = ChatLiteLLM(temperature=0.1, model_name=GPT_MODEL, api_key=ANTHROPIC_API_KEY)
        self.llm = ChatLiteLLM(temperature=1, model_name=GPT_MODEL)
        self.conversation_history = ["N/A"]
        self.use_tools = use_tools
        self.current_turn = 0
        self.first_turn = True
        self.sales_agent = self.initialize_agent()



    # The SalesGPT instance holds a refernece to the SalesGPT instance through the self.sales_agent attribute
    def initialize_agent(self):
        if self.config_path == "":
            print("No agent config specified, using a standard config")
            if self.use_tools:
                print("USING TOOLS")
                sales_agent = SalesGPT.from_llm(
                    self.llm,
                    use_tools=True,
                    product_catalog="examples/sample_product_catalog.txt",
                    salesperson_name="Ted Lasso",
                    verbose=self.verbose,
                )
            else:
                sales_agent = SalesGPT.from_llm(self.llm, verbose=self.verbose)
        else:
            with open(self.config_path, "r") as f:
                config = json.load(f)
            if self.verbose:
                print(f"Agent config {config}")
            if self.use_tools:
                print("USING TOOLS")
                config["use_tools"] = True
                config["product_catalog"] = "examples/sample_product_catalog.txt"
            else:
                config.pop("use_tools", None)  # Remove the use_tools key from config if it exists
            sales_agent = SalesGPT.from_llm(self.llm, verbose=self.verbose, **config)
        # print(f"SalesGPT use_tools: {sales_agent.use_tools}")  # Print the use_tools value of the SalesGPT instance
        sales_agent.seed_agent()
        return sales_agent





    async def run_chains(self, conversation_history, human_response, agent_response):
        try:
    
            # Update the sales agent's conversation history with the provided conversation_history
            self.sales_agent.conversation_history = conversation_history if isinstance(conversation_history, list) else []
            print("Updated conversation history going into running the chains:", conversation_history)

            self.sales_agent.human_response = human_response
            print("Updated human response going into running the chains:", human_response)

            self.sales_agent.agent_response = agent_response
            print("Updated agent response going into running the chains:", agent_response)

            # Set goal_completeness_status before running async_chain_runner
            self.sales_agent.goal_completeness_status = self.sales_agent.goal_completeness_status or "N/A"

            print(f"EMPATHY STATEMENT 1 - Starting generating the empathy statement text: {datetime.now()}")
            empathy_statement_task = asyncio.create_task(self.sales_agent.run_empathy_statement_chain())

            # if not self.first_turn:
            print(f"FEEDER CHAINS 1 - Starting generating the feeder chain results task text: {datetime.now()}")
            chain_results_task = asyncio.create_task(self.sales_agent.async_chain_runner())
            # else:
            #     await asyncio.sleep(2)
            #     chain_results_task = None

            empathy_statement = await empathy_statement_task
            self.sales_agent.empathy_statement = empathy_statement

            # Return empathy_statement immediately
            print(f"EMPATHY STATEMENT 2 - Finished generating the empathy statement text: {datetime.now()}")
            yield empathy_statement

            if chain_results_task:
                chain_results = await chain_results_task

                # Unpack the chain results
                # self.sales_agent.conversation_summary = chain_results["conversation_summary"]
                self.sales_agent.key_points = chain_results["key_points"]
                self.sales_agent.current_goal_review = chain_results["current_goal_review"]
            else:
                # If it's the first turn, use the existing values
                chain_results = {
                    # "conversation_summary": self.sales_agent.conversation_summary,
                    "key_points": self.sales_agent.key_points,
                    "current_goal_review": self.sales_agent.current_goal_review,
                }

            # Return the rest of the results
            print(f"FEEDER CHAINS 2 - Finished generating the feeder chain results task text: {datetime.now()}")
            yield chain_results

            self.first_turn = False

        except Exception as e:
            print(f"Error in run_chains: {e}")
            print(f"Error in run_chains: {type(e).__name__}: {e}")
            print(traceback.format_exc())
            raise  # Re-raise the exception for the caller to handle


    async def update_conversation_stage(self):
        await self.sales_agent.determine_conversation_stage()

    # This do method essentially just runs the standard non-stream response
    async def do(self, conversation_history: list, human_input=None, empathy_statement=None, key_points=None, current_goal_review=None):
        print("do() method empathy_statement argument:", empathy_statement)
        print("SalesGPTAPI.empathy_statement attribute:", getattr(self, "empathy_statement", None))
        print("SalesGPTAPI.sales_agent.empathy_statement attribute:", getattr(self.sales_agent, "empathy_statement", None))

        ai_log = await self.sales_agent._call({
            "empathy_statement": empathy_statement,
            # "conversation_summary": conversation_summary,
            "key_points": key_points,
            "current_goal_review": current_goal_review,
        })

        return ai_log["text"].rstrip('<END_OF_TURN>')




    # This is probably what I want to use
    # Passes in the conversation history
    async def do_stream(self, conversation_history: [str], human_input=None):
        current_turns = len(conversation_history) + 1
        if current_turns >= self.max_num_turns:
            print("Maximum number of turns reached - ending the conversation.")
            yield ["BOT","In case you'll have any questions - just text me one more time!"]
            raise StopAsyncIteration

        # Don't think this seed_agent is necessary as already run in the initialisation
        self.sales_agent.seed_agent()

        # Updates the conversation history
        self.sales_agent.conversation_history = conversation_history

        # This updates the human input which when I get my main file up and running won't be necessary
        if human_input is not None:
            self.sales_agent.human_step(human_input)


        stream_gen = self.sales_agent.astep(stream=True)
        for model_response in stream_gen:
            for choice in model_response.choices:
                message = choice['delta']['content']
                if message is not None:
                    print(message)  # Print the message to the terminal
                    if "<END_OF_CALL>" in message:
                        print("Sales Agent determined it is time to end the conversation.")
                        yield ["BOT","In case you'll have any questions - just text me one more time!"]
                    yield message
                else:
                    continue