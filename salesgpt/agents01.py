"""
This is agents01.py file
"""

from copy import deepcopy
import asyncio
import logging
from typing import Any, Callable, Dict, List, Union
import time
from pydantic import Field
from datetime import datetime

# from langchain.agents import (AgentExecutor, LLMSingleActionAgent,
#                               create_openai_tools_agent)
# from langchain.chains import LLMChain, RetrievalQA
from langchain.chains.base import Chain
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.language_models.llms import create_base_retry_decorator
from litellm import acompletion
from pydantic import Field
from langchain_core.agents import _convert_agent_action_to_messages,_convert_agent_observation_to_messages
import os

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


# ChatLiteLLM.set_verbose = True

class SalesGPT(Chain):
    """Controller model for the Sales Agent."""

    conversation_history: List[str] = []
    conversation_stage_id: str = "1"
    human_response: str = "N/A - this is the first turn of the conversation."
    agent_response: str = "N/A - this is the first turn of the conversation."

    current_conversation_stage: str = CONVERSATION_STAGES.get("1")
    stage_analyzer_chain: StageAnalyzerChain = Field(...)
    # sales_agent_executor: Union[CustomAgentExecutor, None] = Field(...)
    # knowledge_base: Union[RetrievalQA, None] = Field(...)
    sales_conversation_utterance_chain: SalesConversationChain = Field(...)
    # conversation_summary_chain: ConversationSummaryChain = Field(...)
    conversation_stage_dict: Dict = CONVERSATION_STAGES
    # conversation_goal_target_question_counts: Dict = GOAL_TARGET_QUESTION_COUNTS
    key_points_chain: KeyPointsChain = Field(...)
    empathy_statement_chain: EmpathyStatementChain = Field(...)
    current_goal_review_chain: CurrentGoalReviewChain = Field(...)

    question_count_chain: QuestionCountChain = Field(...)
    goal_completeness_chain: GoalCompletenessChain = Field(...)
    # transition_chain: TransitionChain = Field(...)

    conversation_stage_history: List[str] = []
    stage_counts: Dict[str, int] = {}
    has_progressed: bool = False

    # Add the new attributes here
    turns_per_story_component: Dict[str, int] = {}
    GOAL_TARGET_NUMBERS: Dict[str, List[int]] = GOAL_TARGET_NUMBERS

    time_per_story_component: Dict[str, float] = {}
    story_component_start_time: float = 0.0
    current_stage_start_time: float = 0.0
    interview_start_time: float = Field(default_factory=time.time)  # Add this line

    model_name: str = "gpt-4o" # TODO - make this an env variable
    # model_name: str = "gpt-3.5-turbo-0613" # TODO - make this an env variable
    # model_name: str = "claude-3-haiku-20240307" # TODO - make this an env variable
    # model_name: str = "claude-2" # TODO - make this an env variable
    # model_name: str = "groq/llama2-70b-4096" # TODO - make this an env variable
    # model_name: str = "groq/llama3-70b-8192" # TODO - make this an env variable
    # model_name: str = "groq/mixtral-8x7b-32768" # TODO

    key_points: str = "This is the start of the conversation. There is no conversation history."
    # conversation_summary: str = "This is the start of the conversation. There is no conversation history."
    empathy_statement: str = "N/A"
    current_goal_review: str = "N/A"
    goal_completeness_status: str = "N/A"
    question_count_summary: str = "N/A"

    client_name: str = "Cursor"
    client_product_summary: str = "Cursor is an AI-powered coding assistant designed to help developers write code more efficiently. It provides code suggestions, error diagnostics, and refactoring tools, facilitating faster and more accurate coding across various programming languages. Cursor integrates into development environments, enhancing productivity by automating routine tasks and suggesting optimizations."
    interviewee_name: str = "Fletcher"
    customer_type: str = "Paid"
    lead_interviewer: str = "Franko"
    
    use_tools: bool = False
    salesperson_name: str = "Ted Lasso"
    salesperson_role: str = "Business Development Representative"
    company_name: str = "Sleep Haven"
    company_business: str = "Sleep Haven is a premium mattress company that provides customers with the most comfortable and supportive sleeping experience possible. We offer a range of high-quality mattresses, pillows, and bedding accessories that are designed to meet the unique needs of our customers."
    company_values: str = "Our mission at Sleep Haven is to help people achieve a better night's sleep by providing them with the best possible sleep solutions. We believe that quality sleep is essential to overall health and well-being, and we are committed to helping our customers achieve optimal sleep by offering exceptional products and customer service."
    conversation_purpose: str = "find out whether they are looking to achieve better sleep via buying a premier mattress."
    conversation_type: str = "call"

    def retrieve_conversation_stage(self, key):
        """
        Retrieves the conversation stage based on the provided key.

        This function uses the key to look up the corresponding conversation stage in the conversation_stage_dict dictionary.
        If the key is not found in the dictionary, it defaults to "1".

        Args:
            key (str): The key to look up in the conversation_stage_dict dictionary.

        Returns:
            str: The conversation stage corresponding to the key, or "1" if the key is not found.
        """
        return self.conversation_stage_dict.get(key, "1")

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

    # @time_logger
    def seed_agent(self):
        """
        This method seeds the conversation by setting the initial conversation stage and clearing the conversation history.

        The initial conversation stage is retrieved using the key "1". The conversation history is reset to an empty list.

        Returns:
            None
        """
        self.current_conversation_stage = self.retrieve_conversation_stage("1")
        self.conversation_history = []
        self.conversation_stage_history = []
        self.stage_counts = {}
        self.has_progressed = True
        self.interview_start_time = time.time()
        self.start_call()  # Initialize the timer and reset time-related attributes
        
        print(f"Goal Completeness Status CHECK: {self.goal_completeness_status}")


    # async def async_chain_runner(self):
    #     try:
    #         print(f"Goal Completeness Status CHECK: {self.goal_completeness_status}")
    #         chain_results = await asyncio.gather(
    #         #     self.conversation_summary_chain.ainvoke({
    #         #         "conversation_history": "\n".join(self.conversation_history) if self.conversation_history else "N/A",
    #         #         "client_name": self.client_name,
    #         #         "conversation_summary": self.conversation_summary,
    #         #         "goal_completeness_status": self.goal_completeness_status if hasattr(self, 'goal_completeness_status') else "N/A",
    #         #         "current_conversation_stage": self.current_conversation_stage,
    #         #     }),

    #             self.key_points_chain.ainvoke({
    #                 "conversation_history": "\n".join(self.conversation_history) if self.conversation_history else "N/A",
    #                 "client_name": self.client_name,
    #                 "human_response": self.human_response,
    #                 "agent_response": self.agent_response,
    #                 "current_conversation_stage": self.current_conversation_stage, 
    #             }),
                
    #             self.current_goal_review_chain.ainvoke({
    #                 "conversation_history": "\n".join(self.conversation_history) if self.conversation_history else "N/A",
    #                 "current_conversation_stage": self.current_conversation_stage,
    #                 "client_name": self.client_name,
    #                 "interviewee_name": self.interviewee_name,
    #                 "goal_completeness_status": self.goal_completeness_status if hasattr(self, 'goal_completeness_status') else "N/A",
    #                 "customer_type": self.customer_type,
    #                 "has_progressed": self.has_progressed,
    #                 "human_response": self.human_response,
    #             }),
    #         )

    #         # self.conversation_summary = chain_results[0]["text"]
    #         self.key_points = chain_results[0]["text"]
    #         self.current_goal_review = chain_results[1]["text"]

    #         return {
    #             # "conversation_summary": self.conversation_summary,
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
            print(f"Goal Completeness Status CHECK: {self.goal_completeness_status}")
            print(f"Has Progressed: {self.has_progressed}")

            if self.has_progressed:
                # Only run key_points_chain
                key_points_result = await self.key_points_chain.ainvoke({
                    "conversation_history": "\n".join(self.conversation_history) if self.conversation_history else "N/A",
                    "client_name": self.client_name,
                    "human_response": self.human_response,
                    "agent_response": self.agent_response,
                    "current_conversation_stage": self.current_conversation_stage, 
                })
                self.key_points = key_points_result["text"]
                self.current_goal_review = ""  # Set current_goal_review to blank
            else:
                # Only run current_goal_review_chain
                current_goal_review_result = await self.current_goal_review_chain.ainvoke({
                    "conversation_history": "\n".join(self.conversation_history) if self.conversation_history else "N/A",
                    "current_conversation_stage": self.current_conversation_stage,
                    "client_name": self.client_name,
                    "interviewee_name": self.interviewee_name,
                    "goal_completeness_status": self.goal_completeness_status if hasattr(self, 'goal_completeness_status') else "N/A",
                    "customer_type": self.customer_type,
                    "has_progressed": self.has_progressed,
                    "human_response": self.human_response,
                })
                self.current_goal_review = current_goal_review_result["text"]
                self.key_points = ""  # Set key_points to blank

            return {
                "key_points": self.key_points,
                "current_goal_review": self.current_goal_review,
            }

        except Exception as e:
            print(f"Error in async_chain_runner: {e}")
            print(f"Error in async_chain_runner: {type(e).__name__}: {e}")
            print(traceback.format_exc())
            raise  # Re-raise the exception for the caller to handle



    async def run_empathy_statement_chain(self):
        try:
            empathy_statement_result = await self.empathy_statement_chain.ainvoke({
                "conversation_history": "\n".join(self.conversation_history) if self.conversation_history else "N/A",
                "client_name": self.client_name,  # Include client_name in the dictionary
                "human_response": self.human_response,  # Include human_response in the dictionary
                "agent_response": self.agent_response,  # Include agent_response in
            })
            return empathy_statement_result["text"]

        except Exception as e:
            print(f"Error in run_empathy_statement_chain: {e}")
            print(f"Error in run_empathy_statement_chain: {type(e).__name__}: {e}")
            print(traceback.format_exc())
            raise  # Re-raise the exception for the caller to handle


    async def determine_conversation_stage(self):
        try:

            # Increment turn count for current story component
            self.increment_story_component_turn_count()
            
            # This runs the chain and returns goal_completeness_status
            self.run_goal_completeness_chain()

            # This runs the chain and returns question_count_summary
            self.run_question_count_chain()

            previous_stage_id = self.conversation_stage_id
            try:
                stage_analyzer_output = await self.stage_analyzer_chain.ainvoke(
                    input_data={
                        "conversation_history": "\n".join(self.conversation_history).rstrip("\n"),
                        "conversation_stage_id": self.conversation_stage_id,
                        "conversation_stages": "\n".join(
                            [
                                str(key) + ": " + str(value)
                                for key, value in CONVERSATION_STAGES.items()
                            ]
                        ),
                        # "conversation_summary": self.conversation_summary,
                        "interviewee_name": self.interviewee_name,
                        "customer_type": self.customer_type,
                        "goal_completeness_status": self.goal_completeness_status,
                        "question_count_summary": self.question_count_summary,
                    },
                    return_only_outputs=False,
                )
            except Exception as e:
                print(f"Error during stage analysis: {e}")
                # Optionally, set a default value or perform other error handling
                stage_analyzer_output = {"text": "default_stage_id"}  # Example default value


            # This sets the new conversation_stage_id - the main output
            self.conversation_stage_id = stage_analyzer_output.get("text")

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

            print(f"Current Conversation Stage: {self.current_conversation_stage}")
            print(f"Conversation Stage History: {self.conversation_stage_history}")
            print(f"Stage Counts: {self.stage_counts}")
            print(f"Has Progressed: {self.has_progressed}")
        
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
            print(f"Has Progressed Boolean: Current Stage: {current_stage}, Previous Stage: {previous_stage}, Has Progressed: {result}")
            return result
        return False


    def count_conversation_stages(self):
        stage_counts = {}
        for stage_id in self.conversation_stage_history:
            if stage_id not in stage_counts:
                stage_counts[stage_id] = 0
            stage_counts[stage_id] += 1
        print(f"Count Conversation Stages: {stage_counts}")
        print(f"Conversation Stage History: {self.conversation_stage_history}")
        return stage_counts


    def run_question_count_chain(self):
        try:
            question_metrics = self.get_question_count_metrics()
            time_metrics = self.get_time_metrics()
            overall_time_metrics = self.track_overall_interview_time()
            
            question_count_result = self.question_count_chain.invoke(
                input_data={
                    # "conversation_history": "\n".join(self.conversation_history),
                    # "client_name": self.client_name,
                    # "conversation_stage_id": self.conversation_stage_id,
                    # "interviewee_name": self.interviewee_name,
                    # "stage_counts": self.stage_counts, 
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
                    "goal_completeness_status": self.goal_completeness_status
                }
            )
            self.question_count_summary = question_count_result["text"]
            
            # Print metrics (you can keep or remove this based on your debugging needs)
            print(f"Question Count Summary: {self.question_count_summary}")
            print(f"Current Question Count: {question_metrics['current_count']}")
            print(f"Minimum Question Count: {question_metrics['min_count']}")
            print(f"Target Question Count: {question_metrics['target_count']}")
            print(f"Minimum Question Count Met: {question_metrics['min_met']}")
            print(f"Target Question Count Met: {question_metrics['target_met']}")
            print(f"Current Time: {time_metrics['current_time']:.2f} seconds")
            print(f"Minimum Time: {time_metrics['min_time']} seconds")
            print(f"Target Time: {time_metrics['target_time']} seconds")
            print(f"Minimum Time Met: {time_metrics['min_time_met']}")
            print(f"Target Time Met: {time_metrics['target_time_met']}")
            print(f"Overall Time Met: {overall_time_metrics['overall_time_met']}")
            print(f"Overall Elapsed Time: {overall_time_metrics['overall_elapsed_time']:.2f} seconds")
            print(f"Overall Target Time: {overall_time_metrics['overall_target_time']} seconds")
            print(f"Goal Completeness Status: {self.goal_completeness_status}") 

        except Exception as e:
            print(f"An error occurred in run_question_count_chain: {e}")

    def run_goal_completeness_chain(self):
        try:
            goal_completeness_result = self.goal_completeness_chain.invoke(
                input_data={
                    "client_name": self.client_name,
                    "conversation_history": "\n".join(self.conversation_history),
                    "current_conversation_stage": self.current_conversation_stage,
                    "has_progressed": self.has_progressed,
                    "human_response": self.human_response,
                }
            )
            self.goal_completeness_status = goal_completeness_result["text"]
            print(f"Goal Completeness Status: {self.goal_completeness_status}")
        except Exception as e:
            print(f"An error occurred in run_goal_completeness_chain: {e}")
            # Optionally, set a default value or perform other error handling
            self.goal_completeness_status = "Error determining goal completeness"
            print(f"Default Goal Completeness Status set due to error: {self.goal_completeness_status}")


    def update_story_component_time(self):
        current_time = time.time()
        if self.current_stage_start_time > 0:
            elapsed_time = current_time - self.current_stage_start_time
            self.time_per_story_component[self.conversation_stage_id] = elapsed_time
    
    def start_call(self):
        self.current_stage_start_time = time.time()
        self.time_per_story_component = {}
        self.story_component_start_time = 0.0


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

    def increment_story_component_turn_count(self):
        story_component_stage_id = self.conversation_stage_id
        if story_component_stage_id not in self.turns_per_story_component:
            self.turns_per_story_component[story_component_stage_id] = 0
        else:
            self.turns_per_story_component[story_component_stage_id] += 1
        print(f"Turn count for story component {story_component_stage_id}: {self.turns_per_story_component[story_component_stage_id]}")


    def track_overall_interview_time(self):
        current_time = time.time()
        overall_elapsed_time = current_time - self.interview_start_time
        story_component_stage_id = self.conversation_stage_id
        _, _, _, _, overall_target_time = self.GOAL_TARGET_NUMBERS.get(story_component_stage_id, (0, 0, 0, 0, 0))
        overall_time_met = overall_elapsed_time >= overall_target_time
        return {
            "overall_elapsed_time": overall_elapsed_time,
            "overall_target_time": overall_target_time,
            "overall_time_met": overall_time_met
        }

    # TO BE DELETED
    # def run_transition_chain(self):
    #     transition_result = self.transition_chain.invoke(
    #         input={
    #             "interviewee_name": self.interviewee_name,
    #             "has_progressed": self.has_progressed,
    #             "current_conversation_stage": self.current_conversation_stage,
    #             "client_name": self.client_name,
    #             "lead_interviewer": self.lead_interviewer,
    #         }
    #     )
    #     self.transition_statement_status = transition_result["text"]
        


    # def human_step(self, human_input):
    #     """
    #     Processes the human input and appends it to the conversation history.

    #     This method takes the human input as a string, formats it by adding "User: " at the beginning and " <END_OF_TURN>" at the end, and then appends this formatted string to the conversation history.

    #     Args:
    #         human_input (str): The input string from the human user.

    #     Returns:
    #         None
    #     """
    #     human_input = "User: " + human_input + " <END_OF_TURN>"
    #     self.conversation_history.append(human_input)

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
        print(f"Inputs in _call method: {inputs}")
        """
        Executes one step of the sales agent.

        This function overrides the input temporarily with the current state of the conversation,
        generates the agent's utterance using either the sales agent executor or the sales conversation utterance chain,
        adds the agent's response to the conversation history, and returns the AI message.

        Parameters
        ----------
        inputs : Dict[str, Any]
            The initial inputs for the sales agent.

        Returns
        -------
        Dict[str, Any]
            The AI message generated by the sales agent.
        """
        # override inputs temporarily
        inputs = {
            "input": "",
            "conversation_stage": self.current_conversation_stage,
            "conversation_history": "\n".join(self.conversation_history) if self.conversation_history else "N/A",
            "salesperson_name": self.salesperson_name,
            "salesperson_role": self.salesperson_role,
            "interviewee_name": self.interviewee_name,
            "customer_type": self.customer_type,
            "client_product_summary": self.client_product_summary,
            "company_name": self.company_name,
            "company_business": self.company_business,
            "company_values": self.company_values,
            "conversation_purpose": self.conversation_purpose,
            "conversation_type": self.conversation_type,
            "empathy_statement": inputs.get("empathy_statement", self.empathy_statement),
            # "conversation_summary": inputs.get("conversation_summary", self.conversation_summary),
            "key_points": inputs.get("key_points", self.key_points),
            "current_goal_review": inputs.get("current_goal_review", self.current_goal_review),
            "client_name": self.client_name,
            "agent_response": self.agent_response,
            "human_response": self.human_response,
            "has_progressed": self.has_progressed,
            "current_conversation_stage": self.current_conversation_stage,
        }

        # Generate agent's utterance
        # if self.use_tools:
        #     ai_message = await self.sales_agent_executor.ainvoke(inputs)
        #     output = ai_message["output"]
        # else:
        ai_message = await self.sales_conversation_utterance_chain.ainvoke(inputs)
        output = ai_message["text"]

        # # Add agent's response to conversation history
        # agent_name = self.salesperson_name
        # output = f"{agent_name}: {output}"
        # if "<END_OF_TURN>" not in output:
        #     output += " <END_OF_TURN>"
        # self.conversation_history.append(output)

        # if self.verbose:
        #     tool_status = "USE TOOLS INVOKE:" if self.use_tools else "WITHOUT TOOLS:"
        #     print(f"{tool_status}\nAI Message: {ai_message}\nOutput: {output.replace('<END_OF_TURN>', '')}")

        return ai_message

    # @classmethod
    # def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False, **kwargs) -> "SalesGPT":
    #     """
    #     Class method to initialize the SalesGPT Controller from a given ChatLiteLLM instance.

    #     This method sets up the stage analyzer chain and sales conversation utterance chain. It also checks if custom prompts
    #     are to be used and if tools are to be set up for the agent. If tools are to be used, it sets up the knowledge base,
    #     gets the tools, sets up the prompt, and initializes the agent with the tools. If tools are not to be used, it sets
    #     the sales agent executor and knowledge base to None.

    #     Parameters
    #     ----------
    #     llm : ChatLiteLLM
    #         The ChatLiteLLM instance to initialize the SalesGPT Controller from.
    #     verbose : bool, optional
    #         If True, verbose output is enabled. Default is False.
    #     \*\*kwargs : dict
    #         Additional keyword arguments.

    #     Returns
    #     -------
    #     SalesGPT
    #         The initialized SalesGPT Controller.
    #     """
    #     question_count_chain = QuestionCountChain.from_llm(llm, verbose=verbose)
    #     goal_completeness_chain = GoalCompletenessChain.from_llm(llm, verbose=verbose)
    #     # transition_chain = TransitionChain.from_llm(llm, verbose=verbose)
        
    #     stage_analyzer_chain = StageAnalyzerChain.from_llm(llm, verbose=verbose)
    #     sales_conversation_utterance_chain = SalesConversationChain.from_llm(llm, verbose=verbose)
    #     # conversation_summary_chain = ConversationSummaryChain.from_llm(llm, verbose=verbose)
    #     key_points_chain = KeyPointsChain.from_llm(llm, verbose=verbose)
    #     empathy_statement_chain = EmpathyStatementChain.from_llm(llm, verbose=verbose)
    #     current_goal_review_chain = CurrentGoalReviewChain.from_llm(llm, verbose=verbose)

    #     # Handle custom prompts
    #     use_custom_prompt = kwargs.pop("use_custom_prompt", False)
    #     custom_prompt = kwargs.pop("custom_prompt", None)
        
    #     sales_conversation_utterance_chain = SalesConversationChain.from_llm(
    #         llm,
    #         verbose=verbose,
    #         use_custom_prompt=use_custom_prompt,
    #         custom_prompt=custom_prompt,
    #     )

    #     # Handle tools
    #     use_tools_value = kwargs.pop("use_tools", False)
    #     if isinstance(use_tools_value, str):
    #         if use_tools_value.lower() not in ["true", "false"]:
    #             raise ValueError("use_tools must be 'True', 'False', True, or False")
    #         use_tools = use_tools_value.lower() == "true"
    #     elif isinstance(use_tools_value, bool):
    #         use_tools = use_tools_value
    #     else:
    #         raise ValueError("use_tools must be a boolean or a string ('True' or 'False')")
    #     sales_agent_executor = None
    #     knowledge_base = None
        
    #     if use_tools:
    #         product_catalog = kwargs.pop("product_catalog", None)
    #         knowledge_base = setup_knowledge_base(product_catalog)
    #         tools = get_tools(knowledge_base)

    #         prompt = CustomPromptTemplateForTools(
    #             template=SALES_AGENT_TOOLS_PROMPT,
    #             tools_getter=lambda x: tools,
    #             input_variables=[
    #                 "input",
    #                 "intermediate_steps",
    #                 "salesperson_name",
    #                 "salesperson_role",
    #                 "company_name",
    #                 "company_business",
    #                 "company_values",
    #                 "conversation_purpose",
    #                 "conversation_type",
    #                 "conversation_history",
    #             ],
    #         )
    #         llm_chain = LLMChain(llm=llm, prompt=prompt, verbose=verbose)
    #         tool_names = [tool.name for tool in tools]
    #         output_parser = SalesConvoOutputParser(ai_prefix=kwargs.get("salesperson_name", ""))
    #         sales_agent_with_tools = LLMSingleActionAgent(
    #             llm_chain=llm_chain,
    #             output_parser=output_parser,
    #             stop=["\nObservation:"],
    #             allowed_tools=tool_names,
    #         )

    #         sales_agent_executor = CustomAgentExecutor.from_agent_and_tools(
    #             agent=sales_agent_with_tools, tools=tools, verbose=verbose, return_intermediate_steps=True
    #         )


    #     sales_gpt_instance = cls(
    #         question_count_chain=question_count_chain,
    #         goal_completeness_chain=goal_completeness_chain,
    #         # transition_chain=transition_chain,
    #         stage_analyzer_chain=stage_analyzer_chain,
    #         sales_conversation_utterance_chain=sales_conversation_utterance_chain,
    #         # conversation_summary_chain=conversation_summary_chain,
    #         key_points_chain=key_points_chain,
    #         empathy_statement_chain=empathy_statement_chain,
    #         current_goal_review_chain=current_goal_review_chain,
    #         sales_agent_executor=sales_agent_executor,
    #         knowledge_base=knowledge_base,
    #         model_name=llm.model,
    #         verbose=verbose,
    #         use_tools=use_tools,
    #         **kwargs,
    #     )

    #     sales_gpt_instance.conversation_stage_dict = {
    #         key: value.format(
    #             interviewee_name=sales_gpt_instance.interviewee_name,
    #             client_name=sales_gpt_instance.client_name,
    #             customer_type=sales_gpt_instance.customer_type,
    #         )
    #         for key, value in CONVERSATION_STAGES.items()
    #     }

    #     return sales_gpt_instance


    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False, **kwargs) -> "SalesGPT":

        max_tokens = 8192  # You can adjust this value as needed

        # Create a new LLM instance with the standard context length
        llm_with_context = ChatLiteLLM(
            temperature=llm.temperature,
            model_name=llm.model,
            api_key=os.getenv("OPENAI_API_KEY", ""),
            max_tokens=max_tokens
        )

        question_count_chain = QuestionCountChain.from_llm(llm_with_context, verbose=verbose)
        goal_completeness_chain = GoalCompletenessChain.from_llm(llm_with_context, verbose=verbose)
        stage_analyzer_chain = StageAnalyzerChain.from_llm(llm_with_context, verbose=verbose)
        sales_conversation_utterance_chain = SalesConversationChain.from_llm(
            llm_with_context, 
            verbose=verbose,
            use_custom_prompt=kwargs.get("use_custom_prompt", False),
            custom_prompt=kwargs.get("custom_prompt", None)
        )
        key_points_chain = KeyPointsChain.from_llm(llm_with_context, verbose=verbose)
        empathy_statement_chain = EmpathyStatementChain.from_llm(llm_with_context, verbose=verbose)
        current_goal_review_chain = CurrentGoalReviewChain.from_llm(llm_with_context, verbose=verbose)

        sales_gpt_instance = cls(
            question_count_chain=question_count_chain,
            goal_completeness_chain=goal_completeness_chain,
            stage_analyzer_chain=stage_analyzer_chain,
            sales_conversation_utterance_chain=sales_conversation_utterance_chain,
            key_points_chain=key_points_chain,
            empathy_statement_chain=empathy_statement_chain,
            current_goal_review_chain=current_goal_review_chain,
            # sales_agent_executor=sales_agent_executor,
            # knowledge_base=knowledge_base,
            model_name=llm.model,
            verbose=verbose,
            # use_tools=use_tools,
            **kwargs,
        )

        sales_gpt_instance.conversation_stage_dict = {
            key: value.format(
                interviewee_name=sales_gpt_instance.interviewee_name,
                client_name=sales_gpt_instance.client_name,
                customer_type=sales_gpt_instance.customer_type,
            )
            for key, value in CONVERSATION_STAGES.items()
        }

        return sales_gpt_instance