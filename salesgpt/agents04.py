from copy import deepcopy
import asyncio
import logging
from typing import Any, Callable, Dict, List, Union, Optional
import time
from pydantic import Field
from datetime import datetime
import pytz
import importlib
from salesgpt.client_configs import default

# from langchain.agents import (AgentExecutor, LLMSingleActionAgent,
#                               create_openai_tools_agent)
# from langchain.chains import LLMChain, RetrievalQA
from langchain.chains.base import Chain
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.language_models.llms import create_base_retry_decorator
from litellm import acompletion
from pydantic import Field, BaseModel
from langchain_core.agents import _convert_agent_action_to_messages,_convert_agent_observation_to_messages
import os

# This doesn't create instances of these chains; it just makes the class definitions accessible
# This import happens when the module is first loaded, before any instance is created, i.e. when the app starts (I think)
from salesgpt.chains02 import (
    SalesConversationChain,
    StageAnalyzerChain, 
    # ConversationSummaryChain, 
    KeyPointsChain, 
    EmpathyStatementChain, 
    CurrentGoalReviewChain,
    QuestionCountChain,
    GoalCompletenessChain,
    # TransitionChain,
    VerbatimChain,
    ExploratoryChain,
    ConcreteExampleChain,
    ClosingChain,
    ExploratoryChain1,
    ExploratoryChain2,
    ExploratoryChain3,
    SelectorChain,   
)


# from salesgpt.logger import time_logger, logger
from salesgpt.parsers import SalesConvoOutputParser
# from salesgpt.prompts import SALES_AGENT_TOOLS_PROMPT
from salesgpt.stages02 import CONVERSATION_STAGES, GOAL_TARGET_NUMBERS
# from salesgpt.templates import CustomPromptTemplateForTools
# from salesgpt.tools import get_tools, setup_knowledge_base

# from salesgpt.custom_invoke import CustomAgentExecutor
def _create_retry_decorator(llm: Any) -> Callable[[Any], Any]:
    """
    Creates a retry decorator for handling OpenAI API errors.

    This function creates a retry decorator that will retry a function call
    if it raises any of the specified OpenAI API errors. The maximum number of retries
    is determined by the 'max_retries' attribute of the 'llm' object.

    Args:
        llm (Any): An object that has a 'max_retries' attribute specifying the maximum number of retries.

    Returns:
        Callable[[Any], Any]: A retry decorator.
    """
    import openai

    errors = [
        openai.Timeout,
        openai.APIError,
        openai.APIConnectionError,
        openai.RateLimitError,
        openai.APIStatusError,
    ]
    return create_base_retry_decorator(error_types=errors, max_retries=llm.max_retries)

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)



logging.getLogger("requests").setLevel(logging.WARNING)
logging.basicConfig(level=logging.WARNING)  # Set global logging level
logging.getLogger().setLevel(logging.WARNING)  # Set root logger level





class SalesGPT(Chain):
    """Controller model for the Sales Agent."""

    # Attributes that are initialized in __init__ and potentially used across multiple conversations
    stage_analyzer_chain: StageAnalyzerChain = Field(...)
    sales_conversation_utterance_chain: SalesConversationChain = Field(...)
    key_points_chain: KeyPointsChain = Field(...)
    empathy_statement_chain: EmpathyStatementChain = Field(...)
    current_goal_review_chain: CurrentGoalReviewChain = Field(...)
    question_count_chain: QuestionCountChain = Field(...)
    goal_completeness_chain: GoalCompletenessChain = Field(...)

    verbatim_chain: VerbatimChain = Field(...)
    exploratory_chain: ExploratoryChain = Field(...)
    concrete_example_chain: ConcreteExampleChain = Field(...)
    closing_chain: ClosingChain = Field(...)
    exploratory_chain1: ExploratoryChain1 = Field(...)
    exploratory_chain2: ExploratoryChain2 = Field(...)
    exploratory_chain3: ExploratoryChain3 = Field(...)
    selector_chain: SelectorChain = Field(...)

    # Attributes that may change per conversation (initialized in __init__)
    call_id: str = Field(default="")
    model_name: str = Field(default="gpt-4o")
    client_name: str = Field(default="")
    client_product_summary: Optional[str] = Field(default=None)
    interviewee_name: str = Field(default="")
    customer_type: Optional[str] = Field(default=None)
    lead_interviewer: str = Field(default="")
    # use_tools: bool = Field(default=False)
    conversation_type: str = Field(default="call")
    GOAL_TARGET_NUMBERS: Dict[str, List[int]] = Field(default="")
    conversation_stage_dict: Dict[str, str] = Field(default="")

    # Attributes that are reset for each conversation (initialized in seed_agent)
    conversation_history: List[str] = Field(default_factory=list)
    conversation_stage_id: str = Field(default="1")
    human_response: str = Field(default="N/A - this is the first turn of the conversation.")
    agent_response: str = Field(default="N/A - this is the first turn of the conversation.")
    current_conversation_stage: str = Field(default="")
    conversation_stage_history: List[str] = Field(default_factory=list)
    stage_counts: Dict[str, int] = Field(default_factory=dict)
    has_progressed: bool = Field(default=False)
    turns_per_story_component: Dict[str, int] = Field(default_factory=dict)
    time_per_story_component: Dict[str, float] = Field(default_factory=dict)
    story_component_start_time: float = Field(default=0.0)
    current_stage_start_time: float = Field(default=0.0)
    interview_start_time: Optional[float] = Field(default=None)
    key_points: str = Field(default="This is the start of the conversation. There is no conversation history.")
    empathy_statement: str = Field(default="N/A")
    current_goal_review: str = Field(default="N/A")
    goal_completeness_status: str = Field(default="N/A")
    question_count_summary: str = Field(default="N/A")
    to_number: str # Do I need this?
    interviewee_last_name: str = Field(default="") # New
    interviewee_email: str = Field(default="") # New
    # current_date: str = Field(default_factory=lambda: datetime.now(pytz.timezone('America/Los_Angeles')).strftime('%Y-%m-%d'))
    current_date: str = Field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d'))
    conversation_stage_dict: Dict[str, Dict[str, str]] = Field(default="")
    short_conversation_history: List[str] = Field(default_factory=list)



    # def __init__(self, **data):
    #     super().__init__(**data)
    #     self.update_conversation_specific_data()

    def update_conversation_specific_data(self):
        print(f"Updating conversation data for client: {self.client_name}")
        client_module = self.get_client_module(self.client_name)
        print(f"Loaded module: {client_module.__name__}")
        self.GOAL_TARGET_NUMBERS = getattr(client_module, 'GOAL_TARGET_NUMBERS', default.GOAL_TARGET_NUMBERS)
        self.conversation_stage_dict = getattr(client_module, 'CONVERSATION_STAGES', default.CONVERSATION_STAGES)
        self.client_product_summary = getattr(client_module, 'CLIENT_PRODUCT_SUMMARY', default.CLIENT_PRODUCT_SUMMARY)
        # print(f"Loaded GOAL_TARGET_NUMBERS: {self.GOAL_TARGET_NUMBERS}")
        # print(f"Loaded conversation_stage_dict: {self.conversation_stage_dict}")

        # Format the content strings with client_name and other variables
        for key, stage_info in self.conversation_stage_dict.items():
            stage_info['content'] = stage_info['content'].format(
                client_name=self.client_name,
                interviewee_name=self.interviewee_name,
            )

    def get_client_module(self, client_name: str):
        try:
            return importlib.import_module(f'salesgpt.client_configs.{client_name.lower()}')
        except ImportError as e:
            print(f"Warning: No specific configuration found for {client_name}. Error: {e}")
            print("Using default configuration.")
            return importlib.import_module('salesgpt.client_configs.default')

    def seed_agent(self):
        """
        This method seeds the conversation by setting the initial conversation stage and resetting conversation-specific attributes.
        """
        self.update_conversation_specific_data()
        self.conversation_stage_id = "1"
        self.current_conversation_stage = self.retrieve_conversation_stage("1")
        self.conversation_history = []
        self.short_conversation_history = []
        self.conversation_stage_history = []
        self.stage_counts = {}
        self.has_progressed = True
        self.interview_start_time = time.time()
        self.human_response = "N/A - this is the first turn of the conversation."
        self.agent_response = "N/A - this is the first turn of the conversation."
        self.turns_per_story_component = {}
        self.time_per_story_component = {}
        self.story_component_start_time = 0.0
        self.current_stage_start_time = time.time()
        self.key_points = "This is the start of the conversation. There is no conversation history."
        self.empathy_statement = "N/A"
        self.current_goal_review = "N/A"
        self.goal_completeness_status = "N/A"
        self.question_count_summary = "N/A"
        self.start_call()  # Initialize the timer and reset time-related attributes
        # self.update_conversation_specific_data()

    def start_call(self):
        self.current_stage_start_time = time.time()
        self.time_per_story_component = {}
        self.story_component_start_time = 0.0
        self.current_date = datetime.now().strftime('%Y-%m-%d')

    # If using American time zone
    # def start_call(self):
    #     sf_tz = pytz.timezone('America/Los_Angeles')
    #     self.current_stage_start_time = datetime.now(sf_tz).timestamp()
    #     self.time_per_story_component = {}
    #     self.story_component_start_time = 0.0
    #     self.current_date = datetime.now(sf_tz).strftime('%Y-%m-%d')

    def update_short_conversation_history(self, speaker: str, message: str):
        self.short_conversation_history.append(f"{speaker}: {message}")
        # Keep only the last 5 turns (10 messages) in the short history
        if len(self.short_conversation_history) > 10:
            self.short_conversation_history = self.short_conversation_history[-10:]

    def retrieve_conversation_stage(self, key):
        """
        Retrieves the conversation stage content based on the provided key.

        This function uses the key to look up the corresponding conversation stage in the conversation_stage_dict dictionary.
        If the key is not found in the dictionary, it defaults to the content of stage "1".

        Args:
            key (str): The key to look up in the conversation_stage_dict dictionary.

        Returns:
            str: The conversation stage content corresponding to the key, or the content of stage "1" if the key is not found.
        """
        stage_info = self.conversation_stage_dict.get(key, self.conversation_stage_dict["1"])
        return stage_info["content"]

    def get_current_stage_category(self):
        """
        Retrieves the category of the current conversation stage.

        Returns:
            str: The category of the current conversation stage.
        """
        current_stage_info = self.conversation_stage_dict.get(self.conversation_stage_id, self.conversation_stage_dict["1"])
        return current_stage_info["category"]

    # To be deleted
    @property
    def input_keys(self) -> List[str]:
        """
        Property that returns a list of input keys.

        This property is currently set to return an empty list. It can be overridden in a subclass to return a list of keys
        that are used to extract input data from a dictionary.

        Returns:
            List[str]: An empty list.
        """
        return []

    # To be deleted
    @property
    def output_keys(self) -> List[str]:
        """
        Property that returns a list of output keys.

        This property is currently set to return an empty list. It can be overridden in a subclass to return a list of keys
        that are used to extract output data from a dictionary.

        Returns:
            List[str]: An empty list.
        """
        return []
 
    # async def async_chain_runner(self):
    #     try:
    #         print(f"[{datetime.now()}] Async Chain Runner Begun (key points and current goal review)")

    #         print(f"Has Progressed: {self.has_progressed}")

    #         if self.has_progressed:
    #             # Only run key_points_chain
    #             key_points_result = await self.key_points_chain.ainvoke({
    #                 "conversation_history": "\n".join(self.conversation_history) if self.conversation_history else "N/A",
    #                 "client_name": self.client_name,
    #                 "human_response": self.human_response,
    #                 "agent_response": self.agent_response,
    #                 "current_conversation_stage": self.current_conversation_stage, 
    #                 "call_id": self.call_id,
    #                 "interviewee_name": self.interviewee_name, 

    #             })
    #             self.key_points = key_points_result["text"]
    #             self.current_goal_review = ""  # Set current_goal_review to blank
    #         else:
    #             # Only run current_goal_review_chain
    #             current_goal_review_result = await self.current_goal_review_chain.ainvoke({
    #                 "conversation_history": "\n".join(self.conversation_history) if self.conversation_history else "N/A",
    #                 "current_conversation_stage": self.current_conversation_stage,
    #                 "client_name": self.client_name,
    #                 "call_id": self.call_id,
    #                 "interviewee_name": self.interviewee_name, 
    #                 "goal_completeness_status": self.goal_completeness_status if hasattr(self, 'goal_completeness_status') else "N/A",
    #                 "customer_type": self.customer_type,
    #                 "has_progressed": self.has_progressed,
    #                 "human_response": self.human_response,
    #             })
    #             self.current_goal_review = current_goal_review_result["text"]
    #             self.key_points = ""  # Set key_points to blank

    #         print(f"[{datetime.now()}] Async Chain Runner Returned (key points and current goal review)")

    #         return {
    #             "key_points": self.key_points,
    #             "current_goal_review": self.current_goal_review,
    #         }

    #     except Exception as e:
    #         print(f"Error in async_chain_runner: {e}")
    #         print(f"Error in async_chain_runner: {type(e).__name__}: {e}")
    #         print(traceback.format_exc())
    #         raise  # Re-raise the exception for the caller to handle


    async def async_chain_runner(self):
        try:
            print(f"[{datetime.now()}] Async Chain Runner Begun (current goal review)")

            # Always run current_goal_review_chain
            current_goal_review_result = await self.current_goal_review_chain.ainvoke({
                "conversation_history": "\n".join(self.conversation_history) if self.conversation_history else "N/A",
                "short_conversation_history": "\n".join(self.short_conversation_history) if self.short_conversation_history else "N/A",
                "current_conversation_stage": self.current_conversation_stage,
                "client_name": self.client_name,
                "call_id": self.call_id,
                "interviewee_name": self.interviewee_name, 
                "goal_completeness_status": self.goal_completeness_status if hasattr(self, 'goal_completeness_status') else "N/A",
                "customer_type": self.customer_type,
                "has_progressed": self.has_progressed,
                "agent_response": self.agent_response,
                "human_response": self.human_response,
                "client_product_summary": self.client_product_summary,
            })
            self.current_goal_review = current_goal_review_result["text"]

            print(f"[{datetime.now()}] Async Chain Runner Returned (current goal review)")

            return {
                "current_goal_review": self.current_goal_review,
            }

        except Exception as e:
            print(f"Error in async_chain_runner: {e}")
            print(f"Error in async_chain_runner: {type(e).__name__}: {e}")
            print(traceback.format_exc())
            raise  # Re-raise the exception for the caller to handle

    # With additional of Empathy statement insert
    async def run_empathy_statement_chain(self):
        try:
            print(f"[{datetime.now()}] Run Empathy Statement Chain Begun")
            empathy_statement_result = await self.empathy_statement_chain.ainvoke({
                "conversation_history": "\n".join(self.conversation_history) if self.conversation_history else "N/A",
                "short_conversation_history": "\n".join(self.short_conversation_history) if self.short_conversation_history else "N/A",
                "client_name": self.client_name,
                "human_response": self.human_response,
                "agent_response": self.agent_response,
                "call_id": self.call_id,
                "interviewee_name": self.interviewee_name, 
            })
            
            # Insert text at the beginning and end of the empathy statement
            empathy_statement_result["text"] = (
                f'{empathy_statement_result["text"]}<break time="1.0s" />'
            )
            
            print(f"[{datetime.now()}] Run Empathy Statement Chain Returned")
            return empathy_statement_result["text"]
        except Exception as e:
            print(f"Error in run_empathy_statement_chain: {e}")
            print(traceback.format_exc())
            raise


    async def determine_conversation_stage(self):
        try:
            print(f"[{datetime.now()}] Determine Conversation Stage Begun")
            
            # # Create tasks for potentially long-running operations
            # increment_task = asyncio.create_task(self.increment_story_component_turn_count())
            # # goal_completeness_task = asyncio.create_task(self.run_goal_completeness_chain())
            # question_count_task = asyncio.create_task(self.run_question_count_chain())

            # # # Await all tasks concurrently
            # # await asyncio.gather(increment_task, goal_completeness_task, question_count_task)

            # # Await all tasks concurrently
            # await asyncio.gather(increment_task, question_count_task)

            # First, increment the turn count
            await self.increment_story_component_turn_count()
        
            # Then, run the question count chain
            await self.run_question_count_chain()


            previous_stage_id = self.conversation_stage_id
            try:
                print(f"[{datetime.now()}] Stage Analyzer Chain Begun")
                stage_analyzer_output = await self.stage_analyzer_chain.ainvoke(
                    input_data={
                        "conversation_history": "\n".join(self.conversation_history).rstrip("\n"),
                        "short_conversation_history": "\n".join(self.short_conversation_history) if self.short_conversation_history else "N/A",
                        "conversation_stage_id": self.conversation_stage_id,
                        "conversation_stages": "\n".join(
                            [
                                str(key) + ": " + str(value)
                                for key, value in CONVERSATION_STAGES.items()
                            ]
                        ),
                        # "conversation_summary": self.conversation_summary,
                        "call_id": self.call_id,
                        "interviewee_name": self.interviewee_name, 
                        "customer_type": self.customer_type,
                        "goal_completeness_status": self.goal_completeness_status,
                        "question_count_summary": self.question_count_summary,
                        "client_name": self.client_name,
                    },
                    return_only_outputs=False,
                )
                print(f"[{datetime.now()}] Stage Analyzer Chain Returned")
            except Exception as e:
                print(f"Error during stage analysis: {e}")
                stage_analyzer_output = {"text": self.conversation_stage_id}

            # Extract the stage ID from the output
            stage_analyzer_text = stage_analyzer_output.get("text", "")
            import re
            match = re.search(r'<<<<<(\d+)>>>>>', stage_analyzer_text)
            if match:
                new_stage_id = match.group(1)
                print(f"[{datetime.now()}] New conversation stage ID set: {new_stage_id}")
                self.conversation_stage_id = new_stage_id
            else:
                print("No valid stage ID found in the output. Keeping current stage ID.")


            if self.conversation_stage_id != previous_stage_id:
                self.update_story_component_time()  # Update time for the previous stage
                self.current_stage_start_time = time.time()  # Reset timer for the new stage

            # This adds it to the conversation_stage_history which is an input for the conversation stage counts
            self.conversation_stage_history.append(self.conversation_stage_id)

            # This updates the text of the current goal
            self.current_conversation_stage = self.retrieve_conversation_stage(
                self.conversation_stage_id
            )

            # 
            self.stage_counts = self.count_conversation_stages()
            self.has_progressed = self.has_progressed_analysis()  
            # self.run_transition_chain() - TO BE DELETED

            print(f"[{datetime.now()}] Determine Conversation Stage Returned")
        
        except AttributeError as e:
            print(f"AttributeError in determine_conversation_stage: {e}")
        # Handle the error appropriately
        except KeyError as e:
            print(f"KeyError in determine_conversation_stage: {e}")
        # Handle the error appropriately    
        except Exception as e:
            print(f"An error occurred in determine_conversation_stage: {e}")

    
    def has_progressed_analysis(self):
        if len(self.conversation_stage_history) > 1:
            current_stage = self.conversation_stage_history[-1]
            previous_stage = self.conversation_stage_history[-2]
            result = int(current_stage) == int(previous_stage) + 1
            # print(f"Has Progressed Boolean: Current Stage: {current_stage}, Previous Stage: {previous_stage}, Has Progressed: {result}")
            return result
        return False


    def count_conversation_stages(self):
        stage_counts = {}
        for stage_id in self.conversation_stage_history:
            if stage_id not in stage_counts:
                stage_counts[stage_id] = 0
            stage_counts[stage_id] += 1
        # print(f"Count Conversation Stages: {stage_counts}")
        # print(f"Conversation Stage History: {self.conversation_stage_history}")
        return stage_counts


    async def run_question_count_chain(self):
        try:
            print(f"[{datetime.now()}] Run Question Count Chain Begun")
            question_metrics = self.get_question_count_metrics()
            time_metrics = self.get_time_metrics()
            overall_time_metrics = self.track_overall_interview_time()
            
            question_count_result = await self.question_count_chain.ainvoke(
                input_data={
                    # "conversation_history": "\n".join(self.conversation_history),
                    # "client_name": self.client_name,
                    # "conversation_stage_id": self.conversation_stage_id,
                    # "interviewee_name": self.interviewee_name,
                    # "stage_counts": self.stage_counts,
                    "call_id": self.call_id,
                    "interviewee_name": self.interviewee_name, 
                    "current_question_count": question_metrics["current_count"],
                    "min_question_count": question_metrics["min_count"],
                    "target_question_count": question_metrics["target_count"],
                    "min_question_count_met": question_metrics["min_met"],
                    "target_question_count_met": question_metrics["target_met"],
                    "current_time": time_metrics["current_time"],
                    "min_time": time_metrics["min_time"],
                    "target_time": time_metrics["target_time"],
                    "min_time_met": time_metrics["min_time_met"],
                    "target_time_met": time_metrics["target_time_met"],
                    "overall_time_met": overall_time_metrics["overall_time_met"],
                    "overall_elapsed_time": overall_time_metrics["overall_elapsed_time"],
                    "overall_target_time": overall_time_metrics["overall_target_time"],
                    "goal_completeness_status": self.goal_completeness_status,
                    "client_name": self.client_name,
                }
            )
            self.question_count_summary = question_count_result["text"]
            
            # # Print metrics (you can keep or remove this based on your debugging needs)
            # print(f"Question Count Summary: {self.question_count_summary}")
            # print(f"Current Question Count: {question_metrics['current_count']}")
            # print(f"Minimum Question Count: {question_metrics['min_count']}")
            # print(f"Target Question Count: {question_metrics['target_count']}")
            # print(f"Minimum Question Count Met: {question_metrics['min_met']}")
            # print(f"Target Question Count Met: {question_metrics['target_met']}")
            # print(f"Current Time: {time_metrics['current_time']:.2f} seconds")
            # print(f"Minimum Time: {time_metrics['min_time']} seconds")
            # print(f"Target Time: {time_metrics['target_time']} seconds")
            # print(f"Minimum Time Met: {time_metrics['min_time_met']}")
            # print(f"Target Time Met: {time_metrics['target_time_met']}")
            # print(f"Overall Time Met: {overall_time_metrics['overall_time_met']}")
            # print(f"Overall Elapsed Time: {overall_time_metrics['overall_elapsed_time']:.2f} seconds")
            # print(f"Overall Target Time: {overall_time_metrics['overall_target_time']} seconds")
            # print(f"Goal Completeness Status: {self.goal_completeness_status}") 
            print(f"[{datetime.now()}] Run Question Count Chain Returned")

        except Exception as e:
            print(f"An error occurred in run_question_count_chain: {e}")

    async def run_goal_completeness_chain(self):
        try:
            print(f"[{datetime.now()}] Run Goal Completeness Chain Begun")
            goal_completeness_result = await self.goal_completeness_chain.ainvoke(
                input_data={
                    "client_name": self.client_name,
                    "conversation_history": "\n".join(self.conversation_history),
                    "short_conversation_history": "\n".join(self.short_conversation_history) if self.short_conversation_history else "N/A",
                    "current_conversation_stage": self.current_conversation_stage,
                    "has_progressed": self.has_progressed,
                    "human_response": self.human_response,
                    "call_id": self.call_id,
                    "interviewee_name": self.interviewee_name, 
                }
            )
            self.goal_completeness_status = goal_completeness_result["text"]
            print(f"[{datetime.now()}] Run Goal Completeness Chain Returned")
        except Exception as e:
            print(f"An error occurred in run_goal_completeness_chain: {e}")
            self.goal_completeness_status = "Error determining goal completeness"




    def get_question_count_metrics(self):
        story_component_stage_id = self.conversation_stage_id
        current_count = self.turns_per_story_component.get(story_component_stage_id, 0)
        min_count, target_count, _, _, _ = self.GOAL_TARGET_NUMBERS.get(story_component_stage_id, [0, 0, 0, 0, 0])
        min_met = current_count >= min_count
        target_met = current_count >= target_count
        return {
            "current_count": current_count,
            "min_count": min_count,
            "target_count": target_count,
            "min_met": min_met,
            "target_met": target_met
        }

    def update_story_component_time(self):
        current_time = time.time()
        if self.current_stage_start_time > 0:
            elapsed_time = current_time - self.current_stage_start_time
            self.time_per_story_component[self.conversation_stage_id] = elapsed_time


    def update_story_component_time(self):
        current_time = time.time()
        if self.story_component_start_time > 0:
            elapsed_time = current_time - self.story_component_start_time
            story_component_stage_id = self.conversation_stage_id
            self.time_per_story_component[story_component_stage_id] = self.time_per_story_component.get(story_component_stage_id, 0) + elapsed_time
        self.story_component_start_time = current_time


    def get_time_metrics(self):
        story_component_stage_id = self.conversation_stage_id
        current_time = time.time()
        elapsed_time = current_time - self.current_stage_start_time
        _, _, min_time, target_time, _ = self.GOAL_TARGET_NUMBERS.get(story_component_stage_id, (0, 0, 0, 0, 0))
        min_met = elapsed_time >= min_time
        target_met = elapsed_time >= target_time
        return {
            "current_time": elapsed_time,
            "min_time": min_time,
            "target_time": target_time,
            "min_time_met": min_met,
            "target_time_met": target_met
        }

    async def increment_story_component_turn_count(self):
        print(f"[{datetime.now()}] Increment Story Component Turn Count Begun")
        story_component_stage_id = self.conversation_stage_id
        if story_component_stage_id not in self.turns_per_story_component:
            self.turns_per_story_component[story_component_stage_id] = 0
        else:
            self.turns_per_story_component[story_component_stage_id] += 1
        # print(f"Turn count for story component {story_component_stage_id}: {self.turns_per_story_component[story_component_stage_id]}")
        print(f"[{datetime.now()}] Increment Story Component Turn Count Returned")

    def set_interview_start_time(self):
        self.interview_start_time = time.time()

    def track_overall_interview_time(self):
        if self.interview_start_time is None:
            print("Interview start time has not been set.")
            return None

        current_time = time.time()
        overall_elapsed_time = current_time - self.interview_start_time
        story_component_stage_id = self.conversation_stage_id
        _, _, _, _, overall_target_time = self.GOAL_TARGET_NUMBERS.get(story_component_stage_id, (0, 0, 0, 0, 0))
        overall_time_met = overall_elapsed_time < overall_target_time

        
        # Print the values
        print(f"[{datetime.now()}] Time right now")
        print(f"Overall Interview Time Tracking:")
        print(f"  Overall Elapsed Time: {overall_elapsed_time:.2f} seconds")
        print(f"  Overall Target Time: {overall_target_time} seconds")
        print(f"  Overall Time Met: {overall_time_met}")
        

        return {
            "overall_elapsed_time": overall_elapsed_time,
            "overall_target_time": overall_target_time,
            "overall_time_met": overall_time_met
        }



    # @time_logger
    async def step(self, stream: bool = False):
        """
        Executes a step in the conversation. If the stream argument is set to True, 
        it returns a streaming generator object for manipulating streaming chunks in downstream applications. 
        If the stream argument is set to False, it calls the _call method with an empty dictionary as input.

        Args:
            stream (bool, optional): A flag indicating whether to return a streaming generator object. 
            Defaults to False.

        Returns:
            Generator: A streaming generator object if stream is set to True. Otherwise, it returns None.
        """
        if not stream:
            return await self._call(inputs={})
        else:
            return self._streaming_generator()



    async def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # print(f"Inputs in _call method: {inputs}")
        """
        Executes one step of the sales agent.
        """
        # Get the current stage category
        current_category = self.get_current_stage_category().lower()

        # Prepare inputs
        prepared_inputs = self._prepare_inputs(inputs)

        # Select the appropriate chain based on the category
        if current_category == "verbatim":
            selected_chain = self.verbatim_chain
        elif current_category == "exploratory":
            return await self._run_exploratory_chain(prepared_inputs)
        elif current_category == "concrete_example":
            selected_chain = self.concrete_example_chain
        elif current_category == "closing":
            selected_chain = self.closing_chain
        else:
            # Default to the general sales conversation chain if category is not recognized
            selected_chain = self.sales_conversation_utterance_chain

        # Generate the response using the selected chain
        ai_message = await selected_chain.ainvoke(prepared_inputs)
        output = ai_message["text"]
        
        # Add this print statement
        print(f"[_call output] Full text returned:\n{output}")

        return {"text": output}


    def _prepare_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare inputs for the chains."""
        return {
            "input": "",
            "conversation_stage": self.current_conversation_stage,
            "conversation_history": "\n".join(self.conversation_history) if self.conversation_history else "N/A",
            "short_conversation_history": "\n".join(self.short_conversation_history) if self.short_conversation_history else "N/A",
            "customer_type": self.customer_type,
            "client_product_summary": self.client_product_summary,
            "conversation_type": self.conversation_type,
            "empathy_statement": inputs.get("empathy_statement", self.empathy_statement),
            "key_points": inputs.get("key_points", self.key_points),
            "current_goal_review": inputs.get("current_goal_review", self.current_goal_review),
            "client_name": self.client_name,
            "agent_response": self.agent_response,
            "human_response": self.human_response,
            "has_progressed": self.has_progressed,
            "current_conversation_stage": self.current_conversation_stage,
            "call_id": self.call_id,
            "interviewee_name": self.interviewee_name,
        }


    async def _run_exploratory_chain(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Generate 3 responses
            tasks = [
                self.exploratory_chain1.ainvoke(inputs),
                self.exploratory_chain2.ainvoke(inputs),
                self.exploratory_chain3.ainvoke(inputs)
            ]
            responses = await asyncio.gather(*tasks)

            # Extract the text from each response
            response_texts = [response["text"] for response in responses]

            # Prepare inputs for the selector chain
            selector_inputs = {
                "response1": response_texts[0],
                "response2": response_texts[1],
                "response3": response_texts[2],
                "context": inputs,
                # Add the missing keys
                "human_response": self.human_response,
                "short_conversation_history": "\n".join(self.short_conversation_history) if self.short_conversation_history else "N/A",
                "empathy_statement": self.empathy_statement,
                "agent_response": self.agent_response,
                "current_conversation_stage": self.current_conversation_stage,
                "client_name": self.client_name,
                "call_id": self.call_id
            }

            # Run the selector chain
            selection_result = await self.selector_chain.ainvoke(selector_inputs)

            # Get the selected response number, defaulting to 1 if invalid
            try:
                selected_number = int(selection_result["text"].strip())
                if selected_number not in [1, 2, 3]:
                    print(f"Warning: Invalid selection number {selected_number}. Defaulting to 1.")
                    selected_number = 1
            except ValueError:
                print(f"Warning: Could not convert '{selection_result['text']}' to an integer. Defaulting to 1.")
                selected_number = 1

            # Return the selected response
            return {"text": response_texts[selected_number - 1]}

        except Exception as e:
            print(f"Error in _run_exploratory_chain: {e}")
            # If an error occurs, return the first response or a default message
            default_response = responses[0]["text"] if responses else "I apologize, but I encountered an error while processing the response. Could you please rephrase your question or statement?"
            return {"text": default_response}


    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False, call_id: str = None, **kwargs) -> "SalesGPT":

        max_tokens = 8192  # You can adjust this value as needed

        # Create a new LLM instance with the standard context length
        llm_with_context = ChatLiteLLM(
            temperature=llm.temperature,
            model_name="gpt-4o",
            api_key=os.getenv("OPENAI_API_KEY", ""),
            max_tokens=max_tokens
        )

        question_count_chain = QuestionCountChain.from_llm(llm, verbose=verbose)
        goal_completeness_chain = GoalCompletenessChain.from_llm(llm, verbose=verbose)
        stage_analyzer_chain = StageAnalyzerChain.from_llm(llm, verbose=verbose)
        selector_chain = SelectorChain.from_llm(llm, verbose=verbose)
        exploratory_chain1 = ExploratoryChain1.from_llm(llm, verbose=verbose)
        exploratory_chain2 = ExploratoryChain2.from_llm(llm, verbose=verbose)
        exploratory_chain3 = ExploratoryChain3.from_llm(llm, verbose=verbose)
        sales_conversation_utterance_chain = SalesConversationChain.from_llm(
            llm, 
            verbose=verbose
        )
        key_points_chain = KeyPointsChain.from_llm(
            llm=llm,
            verbose=True,
        )
        empathy_statement_chain = EmpathyStatementChain.from_llm(llm, verbose=verbose)
        current_goal_review_chain = CurrentGoalReviewChain.from_llm(llm, verbose=verbose)

        verbatim_chain = VerbatimChain.from_llm(llm, verbose=verbose)
        exploratory_chain = ExploratoryChain.from_llm(llm, verbose=verbose)
        concrete_example_chain = ConcreteExampleChain.from_llm(llm, verbose=verbose)
        closing_chain = ClosingChain.from_llm(llm, verbose=verbose)

        sales_gpt_instance = cls(
            question_count_chain=question_count_chain,
            goal_completeness_chain=goal_completeness_chain,
            stage_analyzer_chain=stage_analyzer_chain,
            sales_conversation_utterance_chain=sales_conversation_utterance_chain,
            key_points_chain=key_points_chain,
            empathy_statement_chain=empathy_statement_chain,
            current_goal_review_chain=current_goal_review_chain,
            model_name=llm.model,
            verbose=verbose,
            call_id=call_id,
            verbatim_chain=verbatim_chain,
            exploratory_chain=exploratory_chain,
            concrete_example_chain=concrete_example_chain,
            closing_chain=closing_chain,
            exploratory_chain1=exploratory_chain1,
            exploratory_chain2=exploratory_chain2,
            exploratory_chain3=exploratory_chain3,
            selector_chain=selector_chain,
            **kwargs,
        )

        # This populates the conversation_stage_dict with formatted converation stages
        # The conversation_stage_dict is where the current conversation stage pulls the curent convers
        sales_gpt_instance.conversation_stage_dict = {
            key: value.format(
                interviewee_name=sales_gpt_instance.interviewee_name,
                client_name=sales_gpt_instance.client_name,
                customer_type=sales_gpt_instance.customer_type,
            )
            for key, value in CONVERSATION_STAGES.items()
        }

        return sales_gpt_instance