
import replicate
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatLiteLLM
import os

# from salesgpt.logger import time_logger, logger
from salesgpt.prompts import (SALES_AGENT_INCEPTION_PROMPT,
                              STAGE_ANALYZER_INCEPTION_PROMPT)

# from .prompts_folder.conversation_summary import CONVERSATION_SUMMARY_PROMPT
from .prompts_folder.current_goal_review import CURRENT_GOAL_REVIEW_PROMPT
from .prompts_folder.empathy_statement import EMPATHY_STATEMENT_PROMPT
from .prompts_folder.key_points import KEY_POINTS_PROMPT
from .prompts_folder.lead_interviewer import LEAD_INTERVIEWER_PROMPT

from .prompts_folder.question_count import QUESTION_COUNT_PROMPT
from .prompts_folder.stage_analyzer import STAGE_ANALYZER_PROMPT
# from .prompts_folder.transition import TRANSITION_PROMPT
from .prompts_folder.goal_completeness_status import GOAL_COMPLETENESS_STATUS_PROMPT

from .prompts_folder.lead_verbatim import VERBATIM_PROMPT
from .prompts_folder.lead_exploratory import EXPLORATORY_PROMPT
from .prompts_folder.lead_concrete_example import CONCRETE_EXAMPLE_PROMPT
from .prompts_folder.lead_closing import CLOSING_PROMPT


ChatLiteLLM.set_verbose = True

from langchain.chains import LLMChain

from langfuse.callback import CallbackHandler
from langfuse.decorators import langfuse_context, observe
from langfuse import Langfuse
import traceback
import logging
# from langfuse.openai import openai
# from langchain.schema import OutputParserException

from dotenv import load_dotenv

load_dotenv()  # This loads the variables from .env
langfuse = Langfuse()

langfuse_handler = CallbackHandler(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
)


# class TracedLLMChain(LLMChain):
#     """Base chain class with Langfuse tracing integrated."""

#     def invoke(self, input_data: dict, **kwargs) -> dict:
#         config = kwargs.get('config', {})s
#         callbacks = config.get('callbacks', [])
#         callbacks.append(langfuse_handler)
#         config['callbacks'] = callbacks
#         kwargs['config'] = config
#         return super().invoke(input_data, **kwargs)

#     async def ainvoke(self, input_data: dict, **kwargs) -> dict:
#         # Ensure that Langfuse handler is included in the callbacks
#         config = kwargs.get('config', {})
#         callbacks = config.get('callbacks', [])
#         callbacks.append(langfuse_handler)
#         config['callbacks'] = callbacks
#         kwargs['config'] = config
        
#         # Call the superclass ainvoke with the updated config
#         return await super().ainvoke(input_data, **kwargs)

class TracedLLMChain(LLMChain):
    def _get_langfuse_handler(self, input_data):
        return CallbackHandler(
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
            user_id=input_data.get('interviewee_name'),
            session_id=input_data.get('call_id'),
            tags=[input_data.get('client_name', 'unknown_client')],
        )

    def invoke(self, input_data: dict, **kwargs) -> dict:
        config = kwargs.get('config', {})
        callbacks = config.get('callbacks', [])
        callbacks.append(self._get_langfuse_handler(input_data))
        config['callbacks'] = callbacks
        kwargs['config'] = config
        return super().invoke(input_data, **kwargs)

    async def ainvoke(self, input_data: dict, **kwargs) -> dict:
        config = kwargs.get('config', {})
        callbacks = config.get('callbacks', [])
        callbacks.append(self._get_langfuse_handler(input_data))
        config['callbacks'] = callbacks
        kwargs['config'] = config
        return await super().ainvoke(input_data, **kwargs)



# IN USE
class SalesConversationChain(TracedLLMChain):
    """Chain to generate the next utterance for the conversation."""

    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        # llm_alt = ChatLiteLLM(temperature=1, model_name="gpt-4o-2024-08-06", api_key=os.getenv("OPENAI_API_KEY", ""), max_tokens=2000)
        llm_alt = ChatLiteLLM(temperature=0, model_name="claude-3-5-sonnet-20240620", api_key=os.getenv("ANTHROPIC_API_KEY", ""), max_tokens=2000)

        prompt = PromptTemplate(
            template=LEAD_INTERVIEWER_PROMPT,
            input_variables=[
                "conversation_type",
                "conversation_history",
                "short_conversation_history",
                "empathy_statement",
                "key_points",
                "current_goal_review",
                "client_name",
                "client_product_summary",
                "interviewee_name",
                "customer_type",
                "agent_response",
                "human_response",
                "has_progressed",
                "current_conversation_stage",
            ],
        )
        return cls(prompt=prompt, llm=llm_alt, verbose=verbose)


# class ConversationSummaryChain(LLMChain):
#     """Chain to summarize the conversation history."""

#     @classmethod
#     def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
#         """Initialize the chain."""
#         prompt = PromptTemplate(
#             template=CONVERSATION_SUMMARY_PROMPT,
#             input_variables=[
#                 "conversation_history", 
#                 "client_name",
#                 "goal_completeness_status",
#                 "current_conversation_stage",
#                 "conversation_summary",
#             ],
#         )
#         return cls(prompt=prompt, llm=llm, verbose=verbose)


# IN USE
class KeyPointsChain(TracedLLMChain):
    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        
        # llm_alt = ChatLiteLLM(temperature=1, model_name="gpt-4o-2024-08-06", api_key=os.getenv("OPENAI_API_KEY", ""), max_tokens=2000)
        llm_alt = ChatLiteLLM(temperature=0, model_name="claude-3-5-sonnet-20240620", api_key=os.getenv("ANTHROPIC_API_KEY", ""), max_tokens=2000)

        prompt = PromptTemplate(
            template=KEY_POINTS_PROMPT,
            input_variables=[
                "conversation_history",
                "client_name",
                "human_response", 
                "agent_response",
                "current_conversation_stage",
            ],
        )
        return cls(prompt=prompt, llm=llm_alt, verbose=verbose)


# IN USE
class EmpathyStatementChain(TracedLLMChain):
    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        # llm_alt = ChatLiteLLM(temperature=0, model_name="groq/llama3-70b-8192", api_key=os.getenv("GROQ_API_KEY", ""))
        # llm_alt = ChatLiteLLM(temperature=0, model_name="claude-3-opus-20240229", api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        # llm_alt = ChatLiteLLM(temperature=0, model_name="together_ai/meta-llama/Llama-3-70b-chat-hf", api_key="b39a51c976619c8f1e44718c5a0edb7e1780a51ad44667e78931dbe65a2cfb9d")
        # llm_alt = ChatLiteLLM(temperature=1, model_name="gpt-4o-2024-08-06", api_key=os.getenv("OPENAI_API_KEY", ""), max_tokens=2000)
        llm_alt = ChatLiteLLM(temperature=0, model_name="claude-3-5-sonnet-20240620", api_key=os.getenv("ANTHROPIC_API_KEY", ""), max_tokens=2000)

        prompt = PromptTemplate(
            template=EMPATHY_STATEMENT_PROMPT,
            input_variables=[
                "conversation_history",
                "short_conversation_history", 
                "client_name",
                "human_response", 
                "agent_response",
            ],
        )
        return cls(prompt=prompt, llm=llm_alt, verbose=verbose)


# IN USE
class GoalCompletenessChain(TracedLLMChain):
    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        # llm_alt = ChatLiteLLM(temperature=0, model_name="claude-3-opus-20240229", api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        # llm_alt = ChatLiteLLM(temperature=0, model_name="together_ai/meta-llama/Llama-3-70b-chat-hf", api_key="b39a51c976619c8f1e44718c5a0edb7e1780a51ad44667e78931dbe65a2cfb9d")
        # llm_alt = ChatLiteLLM(temperature=1, model_name="gpt-4o-2024-08-06", api_key=os.getenv("OPENAI_API_KEY", ""), max_tokens=2000)
        llm_alt = ChatLiteLLM(temperature=0, model_name="claude-3-5-sonnet-20240620", api_key=os.getenv("ANTHROPIC_API_KEY", ""), max_tokens=2000)
        
        prompt = PromptTemplate(
            template=GOAL_COMPLETENESS_STATUS_PROMPT,
            input_variables=[
                "client_name",
                "conversation_history",
                "short_conversation_history",
                "current_conversation_stage",
                "human_response",
                "has_progressed",
            ],
        )
        return cls(prompt=prompt, llm=llm_alt, verbose=verbose)

# IN USE
# @time_logger
class CurrentGoalReviewChain(TracedLLMChain):
    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        
        # llm_alt = ChatLiteLLM(temperature=1, model_name="gpt-4o-2024-08-06", api_key=os.getenv("OPENAI_API_KEY", ""), max_tokens=2000)
        llm_alt = ChatLiteLLM(temperature=0, model_name="claude-3-5-sonnet-20240620", api_key=os.getenv("ANTHROPIC_API_KEY", ""), max_tokens=2000)

        prompt = PromptTemplate(
            template=CURRENT_GOAL_REVIEW_PROMPT,
            input_variables=[
                "conversation_history",
                "short_conversation_history",
                "client_name", 
                "current_conversation_stage",
                "client_product_summary",
                "goal_completeness_status",
                "interviewee_name",
                "has_progressed",
            ],
        )
        return cls(prompt=prompt, llm=llm_alt, verbose=verbose)


# IN USE
class StageAnalyzerChain(TracedLLMChain):
    """Chain to analyze which conversation stage should the conversation move into."""

    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        """Get the response parser."""
        # llm_alt = ChatLiteLLM(temperature=1, model_name="gpt-4o-2024-08-06", api_key=os.getenv("OPENAI_API_KEY", ""), max_tokens=2000)
        llm_alt = ChatLiteLLM(temperature=0, model_name="claude-3-5-sonnet-20240620", api_key=os.getenv("ANTHROPIC_API_KEY", ""), max_tokens=2000)


        prompt = PromptTemplate(
            template=STAGE_ANALYZER_PROMPT,
            input_variables=[
                "conversation_history",
                "conversation_stage_id",
                # "conversation_stages",
                # "conversation_summary",
                "interviewee_type",
                "interviewee_name",
                "goal_completeness_status",
                "question_count_summary",
            ],
        )
        # print(f"STAGE ANALYZER PROMPT {prompt}")
        return cls(prompt=prompt, llm=llm_alt, verbose=verbose)

# IN USE
class QuestionCountChain(TracedLLMChain):
    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        # llm_alt = ChatLiteLLM(temperature=1, model_name="gpt-4o-2024-08-06", api_key=os.getenv("OPENAI_API_KEY", ""), max_tokens=2000)
        llm_alt = ChatLiteLLM(temperature=0, model_name="claude-3-5-sonnet-20240620", api_key=os.getenv("ANTHROPIC_API_KEY", ""), max_tokens=2000)

        prompt = PromptTemplate(
            template=QUESTION_COUNT_PROMPT,
            input_variables=[
                # "conversation_history",
                # "client_name",
                # "conversation_stage_id",
                "interviewee_name",
                "call_id",
                # "stage_counts",
                "current_question_count",  # Added
                "min_question_count",  # Added
                "target_question_count",  # Added
                "min_question_count_met",  # Added
                "target_question_count_met",  # Added
                "current_time",  # Added
                "min_time",  # Added
                "target_time",  # Added
                "min_time_met",  # Added
                "target_time_met",  # Added
                "overall_time_met",  # Added
                "overall_elapsed_time",  # Added
                # "overall_target_time",  # Added
                "goal_completeness_status"  # Added
            ],
        )
        return cls(prompt=prompt, llm=llm_alt, verbose=verbose)



class VerbatimChain(TracedLLMChain):
    """Chain to generate verbatim responses for the conversation."""

    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        # llm_alt = ChatLiteLLM(temperature=1, model_name="gpt-4o-2024-08-06", api_key=os.getenv("OPENAI_API_KEY", ""), max_tokens=2000)
        llm_alt = ChatLiteLLM(temperature=0, model_name="claude-3-5-sonnet-20240620", api_key=os.getenv("ANTHROPIC_API_KEY", ""), max_tokens=2000)

        prompt = PromptTemplate(
            template=VERBATIM_PROMPT,
            input_variables=[
                "conversation_type",
                "conversation_history",
                "empathy_statement",
                "key_points",
                "current_goal_review",
                "client_name",
                "client_product_summary",
                "interviewee_name",
                "customer_type",
                "agent_response",
                "human_response",
                "has_progressed",
                "current_conversation_stage",
            ],
        )
        return cls(prompt=prompt, llm=llm_alt, verbose=verbose)




class ExploratoryChain(TracedLLMChain):
    """Chain to generate exploratory responses for the conversation."""

    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        # llm_alt = ChatLiteLLM(temperature=1, model_name="gpt-4o-2024-08-06", api_key=os.getenv("OPENAI_API_KEY", ""), max_tokens=2000)
        llm_alt = ChatLiteLLM(temperature=0, model_name="claude-3-5-sonnet-20240620", api_key=os.getenv("ANTHROPIC_API_KEY", ""), max_tokens=2000)

        prompt = PromptTemplate(
            template=EXPLORATORY_PROMPT,
            input_variables=[
                "conversation_type",
                "conversation_history",
                "short_conversation_history",
                "empathy_statement",
                "key_points",
                "current_goal_review",
                "client_name",
                "client_product_summary",
                "interviewee_name",
                "customer_type",
                "agent_response",
                "human_response",
                "has_progressed",
                "current_conversation_stage",
            ],
        )
        return cls(prompt=prompt, llm=llm_alt, verbose=verbose)





class ConcreteExampleChain(TracedLLMChain):
    """Chain to generate concrete example responses for the conversation."""

    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        # llm_alt = ChatLiteLLM(temperature=1, model_name="gpt-4o-2024-08-06", api_key=os.getenv("OPENAI_API_KEY", ""), max_tokens=2000)
        llm_alt = ChatLiteLLM(temperature=0, model_name="claude-3-5-sonnet-20240620", api_key=os.getenv("ANTHROPIC_API_KEY", ""), max_tokens=2000)

        prompt = PromptTemplate(
            template=CONCRETE_EXAMPLE_PROMPT,
            input_variables=[
                "conversation_type",
                "conversation_history",
                "short_conversation_history",
                "empathy_statement",
                "key_points",
                "current_goal_review",
                "client_name",
                "client_product_summary",
                "interviewee_name",
                "customer_type",
                "agent_response",
                "human_response",
                "has_progressed",
                "current_conversation_stage",
            ],
        )
        return cls(prompt=prompt, llm=llm_alt, verbose=verbose)




class ClosingChain(TracedLLMChain):
    """Chain to generate closing responses for the conversation."""

    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        # llm_alt = ChatLiteLLM(temperature=1, model_name="gpt-4o-2024-08-06", api_key=os.getenv("OPENAI_API_KEY", ""), max_tokens=2000)
        llm_alt = ChatLiteLLM(temperature=0, model_name="claude-3-5-sonnet-20240620", api_key=os.getenv("ANTHROPIC_API_KEY", ""), max_tokens=2000)

        prompt = PromptTemplate(
            template=CLOSING_PROMPT,
            input_variables=[
                "conversation_type",
                "conversation_history",
                "short_conversation_history",
                "empathy_statement",
                "key_points",
                "current_goal_review",
                "client_name",
                "client_product_summary",
                "interviewee_name",
                "customer_type",
                "agent_response",
                "human_response",
                "has_progressed",
                "current_conversation_stage",
            ],
        )
        return cls(prompt=prompt, llm=llm_alt, verbose=verbose)

