from copy import deepcopy
import asyncio
import logging
from typing import Any, Callable, Dict, List, Union

from langchain.agents import (AgentExecutor, LLMSingleActionAgent,
                              create_openai_tools_agent)
from langchain.chains import LLMChain, RetrievalQA
from langchain.chains.base import Chain
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.language_models.llms import create_base_retry_decorator
from litellm import acompletion
from pydantic import Field
from langchain_core.agents import _convert_agent_action_to_messages,_convert_agent_observation_to_messages

from salesgpt.chains01 import (
    SalesConversationChain,
    StageAnalyzerChain, 
    ConversationSummaryChain, 
    KeyPointsChain, 
    EmpathyStatementChain, 
    SpecificContextChain, 
    CurrentGoalReviewChain,
    QuestionCountChain,
    GoalCompletenessChain,
    TransitionChain,
)


# from salesgpt.logger import time_logger, logger
from salesgpt.parsers import SalesConvoOutputParser
from salesgpt.prompts import SALES_AGENT_TOOLS_PROMPT
from salesgpt.stages import CONVERSATION_STAGES, GOAL_TARGET_QUESTION_COUNTS
from salesgpt.templates import CustomPromptTemplateForTools
from salesgpt.tools import get_tools, setup_knowledge_base

from salesgpt.custom_invoke import CustomAgentExecutor
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

# logging.basicConfig(
#     level=logging.ERROR,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[logging.StreamHandler()]
# )

class SalesGPT(Chain):
    """Controller model for the Sales Agent."""

    conversation_history: List[str] = []
    conversation_stage_id: str = "1"
    current_conversation_stage: str = CONVERSATION_STAGES.get("1")
    stage_analyzer_chain: StageAnalyzerChain = Field(...)
    sales_agent_executor: Union[CustomAgentExecutor, None] = Field(...)
    knowledge_base: Union[RetrievalQA, None] = Field(...)
    sales_conversation_utterance_chain: SalesConversationChain = Field(...)
    conversation_summary_chain: ConversationSummaryChain = Field(...)
    conversation_stage_dict: Dict = CONVERSATION_STAGES
    conversation_goal_target_question_counts: Dict = GOAL_TARGET_QUESTION_COUNTS
    key_points_chain: KeyPointsChain = Field(...)
    empathy_statement_chain: EmpathyStatementChain = Field(...)
    specific_context_chain: SpecificContextChain = Field(...)
    current_goal_review_chain: CurrentGoalReviewChain = Field(...)

    question_count_chain: QuestionCountChain = Field(...)
    goal_completeness_chain: GoalCompletenessChain = Field(...)
    transition_chain: TransitionChain = Field(...)

    conversation_stage_history: List[str] = []
    stage_counts: Dict[str, int] = {}
    has_progressed: bool = False

    # model_name: str = "gpt-3.5-turbo-0613" # TODO - make this an env variable
    # model_name: str = "claude-3-haiku-20240307" # TODO - make this an env variable
    # model_name: str = "claude-2" # TODO - make this an env variable
    # model_name: str = "groq/llama2-70b-4096" # TODO - make this an env variable
    model_name: str = "groq/llama3-70b-8192" # TODO - make this an env variable
    # model_name: str = "groq/mixtral-8x7b-32768" # TODO

    key_points: str = "TESTING KEY POINTS"
    conversation_summary: str = ""
    empathy_statement: str = "TESTING EMPATHY STATEMENT"
    specific_context: str = ""
    current_goal_review: str = ""
    goal_completeness_status: str = ""
    question_count_summary: str = ""
    transition_statement: str = "N/A"

    client_name: str = "Fletcher"
    client_product_summary: str = ""
    interviewee_name: str = ""
    customer_type: str = ""
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
        self.has_progressed = False

    # # @time_logger
    # def update_conversation_summary(self):
    #     if self.conversation_history:
    #         chain_output = self.conversation_summary_chain.invoke(
    #             input={"conversation_history": "\n".join(self.conversation_history)}
    #         )
    #         self.conversation_summary = chain_output['text']
    #     else:
    #         self.conversation_summary = "No conversation history available yet."
        
        # print(f"Conversation Summary: {self.conversation_summary}")

    # async def async_chain_runner(self):
    #     chain_results = await asyncio.gather(
    #         self.conversation_summary_chain.acall({"conversation_history": "\n".join(self.conversation_history)}),
    #         self.key_points_chain.acall({"conversation_history": "\n".join(self.conversation_history)}),
    #         self.specific_context_chain.acall({"conversation_history": "\n".join(self.conversation_history)}),
    #         self.current_goal_review_chain.acall({"conversation_history": "\n".join(self.conversation_history)}),
    #     )

    #     conversation_summary = chain_results[0]["text"]
    #     key_points = chain_results[1]["text"]
    #     specific_context = chain_results[2]["text"]
    #     current_goal_review = chain_results[3]["text"]

    #     return {
    #         "conversation_summary": conversation_summary,
    #         "key_points": key_points,
    #         "specific_context": specific_context,
    #         "current_goal_review": current_goal_review,
    #     }

    async def async_chain_runner(self):

        chain_results = await asyncio.gather(
            self.conversation_summary_chain.acall({
                "conversation_history": "\n".join(self.conversation_history),
                "client_name": self.client_name
            }),
            self.key_points_chain.acall({
                "conversation_history": "\n".join(self.conversation_history),
                "client_name": self.client_name
            }),
            self.specific_context_chain.acall({
                "conversation_history": "\n".join(self.conversation_history),
                "client_name": self.client_name,
                "client_product_summary": self.client_product_summary
            }),
            self.current_goal_review_chain.acall({
                "conversation_history": "\n".join(self.conversation_history),
                "current_conversation_stage": self.current_conversation_stage,
                "client_name": self.client_name,
                "interviewee_name": self.interviewee_name,
                "customer_type": self.customer_type,
            }),
        )

        self.conversation_summary = chain_results[0]["text"]
        self.key_points = chain_results[1]["text"]
        self.specific_context = chain_results[2]["text"]
        self.current_goal_review = chain_results[3]["text"]

        return {
            "conversation_summary": self.conversation_summary,
            "key_points": self.key_points,
            "specific_context": self.specific_context,
            "current_goal_review": self.current_goal_review,
        }


    async def run_empathy_statement_chain(self):
        empathy_statement_result = await self.empathy_statement_chain.acall({
            "conversation_history": "\n".join(self.conversation_history),
            "client_name": self.client_name  # Include client_name in the dictionary
        })
        return empathy_statement_result["text"]


    # @time_logger
    # def determine_conversation_stage(self):
    #     """
    #     Determines the current conversation stage based on the conversation history.

    #     This method uses the stage_analyzer_chain to analyze the conversation history and determine the current stage.
    #     The conversation history is joined into a single string, with each entry separated by a newline character.
    #     The current conversation stage ID is also passed to the stage_analyzer_chain.

    #     The method then prints the determined conversation stage ID and retrieves the corresponding conversation stage
    #     from the conversation_stage_dict dictionary using the retrieve_conversation_stage method.

    #     Finally, the method prints the determined conversation stage.

    #     Returns:
    #         None
    #     """
    #     # print(f"Conversation Stage ID before analysis: {self.conversation_stage_id}")
    #     # print('Conversation history:')
    #     print(self.conversation_history)
    #     stage_analyzer_output = self.stage_analyzer_chain.invoke(input = {
    #         "conversation_history":"\n".join(self.conversation_history).rstrip("\n"),
    #         "conversation_stage_id":self.conversation_stage_id,
    #         "conversation_stages":"\n".join(
    #             [
    #                 str(key) + ": " + str(value)
    #                 for key, value in CONVERSATION_STAGES.items()
    #             ]
    #         ),
    #         "conversation_summary": self.conversation_summary,
    #         "interviewee_name": self.interviewee_name,
    #         "customer_type": self.customer_type,
    #         },
    #         return_only_outputs=False
    #     )
    #     # print('Stage analyzer output')
    #     # print(stage_analyzer_output)
    #     self.conversation_stage_id = stage_analyzer_output.get("text")
        
    #     self.current_conversation_stage = self.retrieve_conversation_stage(
    #         self.conversation_stage_id
    #     )

        # print(f"Conversation Stage: {self.current_conversation_stage}")


    # async def determine_conversation_stage(self):

    #     # Task 1
    #     # The QuestionCountChain should run here - output should update the question_count_summary variable
    #     # This requires a new method to run the questioncountchain and should include passing in the following variables
    #     # - interviewee_name
    #     # - client_name
    #     # - lead_interviwer
    #     # - stage_counts
    #     # - conversation_stage_id
    #     # - goal_target_question_counts

    #     # Task 2
    #     # The GoalCompletenessChain should run here - output should update the goal_completeness_status variable
    #     # This requires a new method to run the GoalCompletenessChain and should include passing in the following variables
    #     # - client_name
    #     # - current_conversation_stage
    #     # - conversation_history

    #     self.run_question_count_chain()
    #     self.run_goal_completeness_chain()

    #     stage_analyzer_output = await self.stage_analyzer_chain.acall(
    #         inputs={
    #             "conversation_history": "\n".join(self.conversation_history).rstrip("\n"),
    #             "conversation_stage_id": self.conversation_stage_id,
    #             "conversation_stages": "\n".join(
    #                 [
    #                     str(key) + ": " + str(value)
    #                     for key, value in CONVERSATION_STAGES.items()
    #                 ]
    #             ),
    #             "conversation_summary": self.conversation_summary,
    #             "interviewee_name": self.interviewee_name,
    #             "customer_type": self.customer_type,
    #             "goal_completeness_status": self.goal_completeness_status,  # Add this line
    #             "question_count_summary": self.question_count_summary,  # Add this line

    #             # Variables from the updated chain needed to be added here
    #             # including the goal completeness status and question count summary
    #         },
    #         return_only_outputs=False,
    #     )
    #     self.conversation_stage_id = stage_analyzer_output.get("text")
    #     self.conversation_stage_history.append(self.conversation_stage_id)
    #     self.current_conversation_stage = self.retrieve_conversation_stage(
    #         self.conversation_stage_id
    #     )

    #     # Task 3
    #     # The TransitionChain should run here - output should update the transition_statement variable
    #     # This requires a new method to run the TransitionChain and should include passing in the following variables
    #     # - interviewer_name
    #     # - has_progressed
    #     # - current_conversation_stage

    #     # Run count_conversation_stages function
    #     self.stage_counts = self.count_conversation_stages()

    #     # Run transition_statement function
    #     self.has_progressed = self.transition_statement()

    #     # Run transition chain
    #     self.run_transition_chain()


    #     print(f"Current Conversation Stage: {self.current_conversation_stage}")
    #     print(f"Conversation Stage History: {self.conversation_stage_history}")
    #     print(f"Stage Counts: {self.stage_counts}")
    #     print(f"Has Progressed: {self.has_progressed}")

    async def determine_conversation_stage(self):
        try:
            self.run_question_count_chain()
            self.run_goal_completeness_chain()

            stage_analyzer_output = await self.stage_analyzer_chain.acall(
                inputs={
                    "conversation_history": "\n".join(self.conversation_history).rstrip("\n"),
                    "conversation_stage_id": self.conversation_stage_id,
                    "conversation_stages": "\n".join(
                        [
                            str(key) + ": " + str(value)
                            for key, value in CONVERSATION_STAGES.items()
                        ]
                    ),
                    "conversation_summary": self.conversation_summary,
                    "interviewee_name": self.interviewee_name,
                    "customer_type": self.customer_type,
                    "goal_completeness_status": self.goal_completeness_status,
                    "question_count_summary": self.question_count_summary,
                },
                return_only_outputs=False,
            )
            self.conversation_stage_id = stage_analyzer_output.get("text")
            self.conversation_stage_history.append(self.conversation_stage_id)
            self.current_conversation_stage = self.retrieve_conversation_stage(
                self.conversation_stage_id
            )

            self.stage_counts = self.count_conversation_stages()
            self.has_progressed = self.transition_statement()
            self.run_transition_chain()

            print(f"Current Conversation Stage: {self.current_conversation_stage}")
            print(f"Conversation Stage History: {self.conversation_stage_history}")
            print(f"Stage Counts: {self.stage_counts}")
            print(f"Has Progressed: {self.has_progressed}")
        except Exception as e:
            logging.exception("An error occurred in determine_conversation_stage:")

    def transition_statement(self):
        if len(self.conversation_stage_history) > 1:
            current_stage_id = int(self.conversation_stage_id)
            previous_stage_id = int(self.conversation_stage_history[-2])
            result = current_stage_id > previous_stage_id
            print(f"Transition Statement: Current Stage ID: {current_stage_id}, Previous Stage ID: {previous_stage_id}, Has Progressed: {result}")
            return result
        print("Transition Statement: Not enough conversation stages to determine progression")
        return False


    def count_conversation_stages(self):
        stage_counts = {}
        for stage_id in self.conversation_stage_history:
            if stage_id not in stage_counts:
                stage_counts[stage_id] = 0
            stage_counts[stage_id] += 1
        print(f"Count Conversation Stages: {stage_counts}")
        return stage_counts


    def run_question_count_chain(self):
        question_count_result = self.question_count_chain.invoke(
            input={
                "conversation_history": "\n".join(self.conversation_history),
                "client_name": self.client_name,
                "conversation_stage_id": self.conversation_stage_id,
                "interviewee_name": self.interviewee_name,
                "lead_interviewer": self.lead_interviewer,
                "goal_target_question_counts": self.conversation_goal_target_question_counts,
                "stage_counts": self.stage_counts, 
            }
        )
        self.question_count_summary = question_count_result["text"]
    

    def run_goal_completeness_chain(self):
        goal_completeness_result = self.goal_completeness_chain.invoke(
            input={
                "client_name": self.client_name,
                "conversation_history": "\n".join(self.conversation_history),
                "current_conversation_stage": self.current_conversation_stage,
            }
        )
        self.goal_completeness_status = goal_completeness_result["text"]


    def run_transition_chain(self):
        transition_result = self.transition_chain.invoke(
            input={
                "interviewee_name": self.interviewee_name,
                "has_progressed": self.has_progressed,
                "current_conversation_stage": self.current_conversation_stage,
            }
        )
        self.transition_statement = transition_result["text"]


    def human_step(self, human_input):
        """
        Processes the human input and appends it to the conversation history.

        This method takes the human input as a string, formats it by adding "User: " at the beginning and " <END_OF_TURN>" at the end, and then appends this formatted string to the conversation history.

        Args:
            human_input (str): The input string from the human user.

        Returns:
            None
        """
        human_input = "User: " + human_input + " <END_OF_TURN>"
        self.conversation_history.append(human_input)

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

    # This checks streaming is true, if it is, it moves to _astreaming_generator
    # @time_logger
    # async def astep(self, stream: bool = False):
    #     """
    #     Executes an asynchronous step in the conversation. 

    #     If the stream argument is set to False, it calls the _acall method with an empty dictionary as input.
    #     If the stream argument is set to True, it returns a streaming generator object for manipulating streaming chunks in downstream applications.

    #     Args:
    #         stream (bool, optional): A flag indicating whether to return a streaming generator object. 
    #         Defaults to False.

    #     Returns:
    #         Generator: A streaming generator object if stream is set to True. Otherwise, it returns None.
    #     """
    #     if not stream:
    #         self._acall(inputs={})
    #     else:
    #         return await self._astreaming_generator()

    # # @time_logger
    # def acall(self, *args, **kwargs):
    #     """
    #     This method is currently not implemented.

    #     Parameters
    #     ----------
    #     \*args : tuple
    #         Variable length argument list.
    #     \*\*kwargs : dict
    #         Arbitrary keyword arguments.

    #     Raises
    #     ------
    #     NotImplementedError
    #         Indicates that this method has not been implemented yet.
    #     """
    #     raise NotImplementedError("This method has not been implemented yet.")

    # # @time_logger
    # def _prep_messages(self):
    #     """
    #     Prepares a list of messages for the streaming generator.

    #     This method prepares a list of messages based on the current state of the conversation.
    #     The messages are prepared using the 'prep_prompts' method of the 'sales_conversation_utterance_chain' object.
    #     The prepared messages include details about the current conversation stage, conversation history, salesperson's name and role,
    #     company's name, business, values, conversation purpose, and conversation type.

    #     Returns:
    #         list: A list of prepared messages to be passed to a streaming generator.
    #     """
        
    #     prompt = self.sales_conversation_utterance_chain.prep_prompts(
    #         [
    #             dict(
    #                 conversation_stage=self.current_conversation_stage,
    #                 conversation_history="\n".join(self.conversation_history),
    #                 salesperson_name=self.salesperson_name,
    #                 salesperson_role=self.salesperson_role,
    #                 company_name=self.company_name,
    #                 company_business=self.company_business,
    #                 company_values=self.company_values,
    #                 conversation_purpose=self.conversation_purpose,
    #                 conversation_type=self.conversation_type,
    #             )
    #         ]
    #     )

    #     inception_messages = prompt[0][0].to_messages()

    #     message_dict = {"role": "system", "content": inception_messages[0].content}

    #     if self.sales_conversation_utterance_chain.verbose:
    #         pass
    #         #print("\033[92m" + inception_messages[0].content + "\033[0m")
    #     return [message_dict]

    # # @time_logger
    # def _streaming_generator(self):
    #     """
    #     Generates a streaming generator for partial LLM output manipulation.

    #     This method is used when the sales agent needs to take an action before the full LLM output is available.
    #     For example, when performing text to speech on the partial LLM output. The method returns a streaming generator
    #     which can manipulate partial output from an LLM in-flight of the generation.

    #     Returns
    #     -------
    #     generator
    #         A streaming generator for manipulating partial LLM output.

    #     Examples
    #     --------
    #     >>> streaming_generator = self._streaming_generator()
    #     >>> for chunk in streaming_generator:
    #     ...     print(chunk)
    #     Chunk 1, Chunk 2, ... etc.

    #     See Also
    #     --------
    #     https://github.com/openai/openai-cookbook/blob/main/examples/How_to_stream_completions.ipynb
    #     """

    #     messages = self._prep_messages()

    #     return self.sales_conversation_utterance_chain.llm.completion_with_retry(
    #         messages=messages,
    #         stop="<END_OF_TURN>",
    #         stream=True,
    #         model=self.model_name,
    #     )

    # async def acompletion_with_retry(self, llm: Any, **kwargs: Any) -> Any:
    #     """
    #     Use tenacity to retry the async completion call.

    #     This method uses the tenacity library to retry the asynchronous completion call in case of failure.
    #     It creates a retry decorator using the '_create_retry_decorator' method and applies it to the 
    #     '_completion_with_retry' function which makes the actual asynchronous completion call.

    #     Parameters
    #     ----------
    #     llm : Any
    #         The language model to be used for the completion.
    #     \*\*kwargs : Any
    #         Additional keyword arguments to be passed to the completion function.

    #     Returns
    #     -------
    #     Any
    #         The result of the completion function call.

    #     Raises
    #     ------
    #     Exception
    #         If the completion function call fails after the maximum number of retries.
    #     """
    #     retry_decorator = _create_retry_decorator(llm)

    #     @retry_decorator
    #     async def _completion_with_retry(**kwargs: Any) -> Any:
    #         # Use OpenAI's async api https://github.com/openai/openai-python#async-api
    #         return await acompletion(**kwargs)

    #     return await _completion_with_retry(**kwargs)

    # async def _astreaming_generator(self):
    #     """
    #     Asynchronous generator to reduce I/O blocking when dealing with multiple
    #     clients simultaneously.

    #     This function returns a streaming generator which can manipulate partial output from an LLM
    #     in-flight of the generation. This is useful in scenarios where the sales agent wants to take an action 
    #     before the full LLM output is available. For instance, if we want to do text to speech on the partial LLM output.

    #     Returns
    #     -------
    #     AsyncGenerator
    #         A streaming generator which can manipulate partial output from an LLM in-flight of the generation.

    #     Examples
    #     --------
    #     >>> streaming_generator = self._astreaming_generator()
    #     >>> async for chunk in streaming_generator:
    #     >>>     await chunk ...
    #     Out: Chunk 1, Chunk 2, ... etc.

    #     See Also
    #     --------
    #     https://github.com/openai/openai-cookbook/blob/main/examples/How_to_stream_completions.ipynb
    #     """

    #     messages = self._prep_messages()

    #     return await self.acompletion_with_retry(
    #         llm=self.sales_conversation_utterance_chain.llm,
    #         messages=messages,
    #         stop="<END_OF_TURN>",
    #         stream=True,
    #         model=self.model_name,
    #     )
            

    # def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    #     """
    #     Executes one step of the sales agent.

    #     This function overrides the input temporarily with the current state of the conversation,
    #     generates the agent's utterance using either the sales agent executor or the sales conversation utterance chain,
    #     adds the agent's response to the conversation history, and returns the AI message.

    #     Parameters
    #     ----------
    #     inputs : Dict[str, Any]
    #         The initial inputs for the sales agent.

    #     Returns
    #     -------
    #     Dict[str, Any]
    #         The AI message generated by the sales agent.

    #     """
    #     # override inputs temporarily
    #     inputs = {
    #         "input": "",
    #         "conversation_stage": self.current_conversation_stage,
    #         "conversation_history": "\n".join(self.conversation_history),
    #         "salesperson_name": self.salesperson_name,
    #         "salesperson_role": self.salesperson_role,
    #         "company_name": self.company_name,
    #         "company_business": self.company_business,
    #         "company_values": self.company_values,
    #         "conversation_purpose": self.conversation_purpose,
    #         "conversation_type": self.conversation_type,
    #     }

    #     # Generate agent's utterance
    #     if self.use_tools:
    #         ai_message = self.sales_agent_executor.invoke(inputs)
    #         output = ai_message["output"]
    #     else:
    #         ai_message = self.sales_conversation_utterance_chain.invoke(inputs, return_intermediate_steps=True)
    #         output = ai_message["text"]

    #     # Add agent's response to conversation history
    #     agent_name = self.salesperson_name
    #     output = agent_name + ": " + output
    #     if "<END_OF_TURN>" not in output:
    #         output += " <END_OF_TURN>"
    #     self.conversation_history.append(output)

    #     if self.verbose:
    #         tool_status = "USE TOOLS INVOKE:" if self.use_tools else "WITHOUT TOOLS:"
    #         # print(f"{tool_status}\n#\n#\n#\n#\n------------------")
    #         # print(f"AI Message: {ai_message}")
    #         # print()
    #         # print(f"Output: {output.replace('<END_OF_TURN>', '')}")

    #     return ai_message

    # async def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    #     """
    #     Executes one step of the sales agent.

    #     This function overrides the input temporarily with the current state of the conversation,
    #     generates the agent's utterance using either the sales agent executor or the sales conversation utterance chain,
    #     adds the agent's response to the conversation history, and returns the AI message.

    #     Parameters
    #     ----------
    #     inputs : Dict[str, Any]
    #         The initial inputs for the sales agent.

    #     Returns
    #     -------
    #     Dict[str, Any]
    #         The AI message generated by the sales agent.
    #     """
    #     # override inputs temporarily
    #     inputs = {
    #         "input": "",
    #         "conversation_stage": self.current_conversation_stage,
    #         "conversation_history": "\n".join(self.conversation_history),
    #         "salesperson_name": self.salesperson_name,
    #         "salesperson_role": self.salesperson_role,
    #         "company_name": self.company_name,
    #         "company_business": self.company_business,
    #         "company_values": self.company_values,
    #         "conversation_purpose": self.conversation_purpose,
    #         "conversation_type": self.conversation_type,
    #     }

    #     # Run the asynchronous chain runner to get the results from the new chains
    #     chain_results = await self.async_chain_runner()
    #     self.conversation_summary = chain_results["conversation_summary"]
    #     self.key_points = chain_results["key_points"]
    #     self.empathy_statement = chain_results["empathy_statement"]
    #     self.specific_context = chain_results["specific_context"]
    #     self.current_goal_review = chain_results["current_goal_review"]

    #     # Update the inputs dictionary with the results from the new chains
    #     inputs.update({
    #         "conversation_summary": self.conversation_summary,
    #         "key_points": self.key_points,
    #         "empathy_statement": self.empathy_statement,
    #         "specific_context": self.specific_context,
    #         "current_goal_review": self.current_goal_review,
    #     })

    #     # Generate agent's utterance
    #     if self.use_tools:
    #         ai_message = await self.sales_agent_executor.acall(inputs)
    #         output = ai_message["output"]
    #     else:
    #         ai_message = await self.sales_conversation_utterance_chain.acall(inputs)
    #         output = ai_message["text"]

    #     # Add agent's response to conversation history
    #     agent_name = self.salesperson_name
    #     output = f"{agent_name}: {output}"
    #     if "<END_OF_TURN>" not in output:
    #         output += " <END_OF_TURN>"
    #     self.conversation_history.append(output)

    #     if self.verbose:
    #         tool_status = "USE TOOLS INVOKE:" if self.use_tools else "WITHOUT TOOLS:"
    #         print(f"{tool_status}\nAI Message: {ai_message}\nOutput: {output.replace('<END_OF_TURN>', '')}")

    #     return ai_message

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
            "conversation_history": "\n".join(self.conversation_history),
            "salesperson_name": self.salesperson_name,
            "salesperson_role": self.salesperson_role,
            "company_name": self.company_name,
            "company_business": self.company_business,
            "company_values": self.company_values,
            "conversation_purpose": self.conversation_purpose,
            "conversation_type": self.conversation_type,
            "empathy_statement": inputs.get("empathy_statement", self.empathy_statement),
            "conversation_summary": inputs.get("conversation_summary", self.conversation_summary),
            "key_points": inputs.get("key_points", self.key_points),
            "specific_context": inputs.get("specific_context", self.specific_context),
            "current_goal_review": inputs.get("current_goal_review", self.current_goal_review),
            "client_name": self.client_name,
            "transition_statement": inputs.get("transition_statement", self.transition_statement),
        }

        # Generate agent's utterance
        if self.use_tools:
            ai_message = await self.sales_agent_executor.acall(inputs)
            output = ai_message["output"]
        else:
            ai_message = await self.sales_conversation_utterance_chain.acall(inputs)
            output = ai_message["text"]

        # Add agent's response to conversation history
        agent_name = self.salesperson_name
        output = f"{agent_name}: {output}"
        if "<END_OF_TURN>" not in output:
            output += " <END_OF_TURN>"
        self.conversation_history.append(output)

        if self.verbose:
            tool_status = "USE TOOLS INVOKE:" if self.use_tools else "WITHOUT TOOLS:"
            print(f"{tool_status}\nAI Message: {ai_message}\nOutput: {output.replace('<END_OF_TURN>', '')}")

        return ai_message

    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False, **kwargs) -> "SalesGPT":
        """
        Class method to initialize the SalesGPT Controller from a given ChatLiteLLM instance.

        This method sets up the stage analyzer chain and sales conversation utterance chain. It also checks if custom prompts
        are to be used and if tools are to be set up for the agent. If tools are to be used, it sets up the knowledge base,
        gets the tools, sets up the prompt, and initializes the agent with the tools. If tools are not to be used, it sets
        the sales agent executor and knowledge base to None.

        Parameters
        ----------
        llm : ChatLiteLLM
            The ChatLiteLLM instance to initialize the SalesGPT Controller from.
        verbose : bool, optional
            If True, verbose output is enabled. Default is False.
        \*\*kwargs : dict
            Additional keyword arguments.

        Returns
        -------
        SalesGPT
            The initialized SalesGPT Controller.
        """
        question_count_chain = QuestionCountChain.from_llm(llm, verbose=verbose)
        goal_completeness_chain = GoalCompletenessChain.from_llm(llm, verbose=verbose)
        transition_chain = TransitionChain.from_llm(llm, verbose=verbose)
        
        stage_analyzer_chain = StageAnalyzerChain.from_llm(llm, verbose=verbose)
        sales_conversation_utterance_chain = SalesConversationChain.from_llm(llm, verbose=verbose)
        conversation_summary_chain = ConversationSummaryChain.from_llm(llm, verbose=verbose)
        key_points_chain = KeyPointsChain.from_llm(llm, verbose=verbose)
        empathy_statement_chain = EmpathyStatementChain.from_llm(llm, verbose=verbose)
        specific_context_chain = SpecificContextChain.from_llm(llm, verbose=verbose)
        current_goal_review_chain = CurrentGoalReviewChain.from_llm(llm, verbose=verbose)

        # Handle custom prompts
        use_custom_prompt = kwargs.pop("use_custom_prompt", False)
        custom_prompt = kwargs.pop("custom_prompt", None)
        
        sales_conversation_utterance_chain = SalesConversationChain.from_llm(
            llm,
            verbose=verbose,
            use_custom_prompt=use_custom_prompt,
            custom_prompt=custom_prompt,
        )

        # Handle tools
        use_tools_value = kwargs.pop("use_tools", False)
        if isinstance(use_tools_value, str):
            if use_tools_value.lower() not in ["true", "false"]:
                raise ValueError("use_tools must be 'True', 'False', True, or False")
            use_tools = use_tools_value.lower() == "true"
        elif isinstance(use_tools_value, bool):
            use_tools = use_tools_value
        else:
            raise ValueError("use_tools must be a boolean or a string ('True' or 'False')")
        sales_agent_executor = None
        knowledge_base = None
        
        if use_tools:
            product_catalog = kwargs.pop("product_catalog", None)
            knowledge_base = setup_knowledge_base(product_catalog)
            tools = get_tools(knowledge_base)

            prompt = CustomPromptTemplateForTools(
                template=SALES_AGENT_TOOLS_PROMPT,
                tools_getter=lambda x: tools,
                input_variables=[
                    "input",
                    "intermediate_steps",
                    "salesperson_name",
                    "salesperson_role",
                    "company_name",
                    "company_business",
                    "company_values",
                    "conversation_purpose",
                    "conversation_type",
                    "conversation_history",
                ],
            )
            llm_chain = LLMChain(llm=llm, prompt=prompt, verbose=verbose)
            tool_names = [tool.name for tool in tools]
            output_parser = SalesConvoOutputParser(ai_prefix=kwargs.get("salesperson_name", ""))
            sales_agent_with_tools = LLMSingleActionAgent(
                llm_chain=llm_chain,
                output_parser=output_parser,
                stop=["\nObservation:"],
                allowed_tools=tool_names,
            )

            sales_agent_executor = CustomAgentExecutor.from_agent_and_tools(
                agent=sales_agent_with_tools, tools=tools, verbose=verbose, return_intermediate_steps=True
            )

        return cls(
            question_count_chain=question_count_chain,
            goal_completeness_chain=goal_completeness_chain,
            transition_chain=transition_chain,
            stage_analyzer_chain=stage_analyzer_chain,
            sales_conversation_utterance_chain=sales_conversation_utterance_chain,
            conversation_summary_chain=conversation_summary_chain,
            key_points_chain=key_points_chain,
            empathy_statement_chain=empathy_statement_chain,
            specific_context_chain=specific_context_chain,
            current_goal_review_chain=current_goal_review_chain,
            sales_agent_executor=sales_agent_executor,
            knowledge_base=knowledge_base,
            model_name=llm.model,
            verbose=verbose,
            use_tools=use_tools,
            **kwargs,
        )
