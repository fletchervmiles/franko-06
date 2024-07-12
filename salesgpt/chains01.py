"""
This is chains01.py file
"""
import replicate
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatLiteLLM
import os

# from salesgpt.logger import time_logger, logger
from salesgpt.prompts import (SALES_AGENT_INCEPTION_PROMPT,
                              STAGE_ANALYZER_INCEPTION_PROMPT)

from .prompts_folder.conversation_summary import CONVERSATION_SUMMARY_PROMPT
from .prompts_folder.current_goal_review import CURRENT_GOAL_REVIEW_PROMPT
from .prompts_folder.empathy_statement import EMPATHY_STATEMENT_PROMPT
from .prompts_folder.key_points import KEY_POINTS_PROMPT
from .prompts_folder.lead_interviewer import LEAD_INTERVIEWER_PROMPT
from .prompts_folder.specific_context import SPECIFIC_CONTEXT_PROMPT

from .prompts_folder.question_count import QUESTION_COUNT_PROMPT
from .prompts_folder.stage_analyzer import STAGE_ANALYZER_PROMPT
from .prompts_folder.transition import TRANSITION_PROMPT
from .prompts_folder.goal_completeness_status import GOAL_COMPLETENESS_STATUS_PROMPT

ChatLiteLLM.set_verbose = True

# import logging
# logging.getLogger("requests").setLevel(logging.WARNING)
# logging.basicConfig(level=logging.WARNING)  # Set global logging level
# logging.getLogger().setLevel(logging.WARNING)  # Set root logger level

class SalesConversationChain(LLMChain):
    """Chain to generate the next utterance for the conversation."""

    @classmethod
    def from_llm(
        cls,
        llm: ChatLiteLLM,
        verbose: bool = False,
        use_custom_prompt: bool = False,  # Add this line
        custom_prompt: str = "You are an AI Sales agent, sell me this pencil",  # Add this line
    ) -> LLMChain:
        # llm_alt = ChatLiteLLM(temperature=0, model_name="groq/llama3-70b-8192", api_key=os.getenv("GROQ_API_KEY", ""))
        # llm_alt = ChatLiteLLM(temperature=0, model_name="replicate/meta-llama-3-8b-instruct", api_key=os.getenv("REPLICATE_API_TOKEN", ""))
        # llm_alt = ChatLiteLLM(temperature=0, model_name="replicate/meta-llama-3-8b-instruct", api_key="r8_djcrjSEI4A1G50NtubUXgTXkoHT5jmG1XMHoA")
        # llm_alt = ChatLiteLLM(temperature=0, model_name="claude-3-opus-20240229", api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        # llm_alt = ChatLiteLLM(temperature=0, model_name="together_ai/meta-llama/Llama-3-70b-chat-hf", api_key="b39a51c976619c8f1e44718c5a0edb7e1780a51ad44667e78931dbe65a2cfb9d")
        llm_alt = ChatLiteLLM(temperature=1, model_name="gpt-4", api_key=os.getenv("OPENAI_API_KEY", ""))


        if use_custom_prompt:  # Add this block
            prompt = PromptTemplate(
                template=LEAD_INTERVIEWER_PROMPT,
                input_variables=[
                    "salesperson_name",
                    "salesperson_role",
                    "company_name",
                    "company_business",
                    "company_values",
                    "conversation_purpose",
                    "conversation_type",
                    "conversation_history",
                    "empathy_statement",
                    "conversation_summary",
                    "key_points",
                    "specific_context",
                    "current_goal_review",
                    "client_name",
                    "transition_statement_status",
                    "client_product_summary",
                    "interviewee_name",
                    "customer_type",
                    "agent_response",
                    "human_response",
                ],
            )
        else:  # Modify this block to be part of the else condition
            prompt = PromptTemplate(
                template=LEAD_INTERVIEWER_PROMPT,
                input_variables=[
                    "salesperson_name",
                    "salesperson_role",
                    "company_name",
                    "company_business",
                    "company_values",
                    "conversation_purpose",
                    "conversation_type",
                    "conversation_history",
                    "empathy_statement",
                    "conversation_summary",
                    "key_points",
                    "specific_context",
                    "current_goal_review",
                    "client_name",
                    "transition_statement_status",
                    "client_product_summary",
                    "interviewee_name",
                    "customer_type",
                    "agent_response",
                    "human_response",
                ],
            )
        return cls(prompt=prompt, llm=llm_alt, verbose=verbose)


class ConversationSummaryChain(LLMChain):
    """Chain to summarize the conversation history."""

    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        """Initialize the chain."""
        prompt = PromptTemplate(
            template=CONVERSATION_SUMMARY_PROMPT,
            input_variables=[
                "conversation_history", 
                "client_name",
                "goal_completeness_status",
                "current_conversation_stage",
                "conversation_summary",
            ],
        )
        return cls(prompt=prompt, llm=llm, verbose=verbose)



class KeyPointsChain(LLMChain):
    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
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
        return cls(prompt=prompt, llm=llm, verbose=verbose)



class EmpathyStatementChain(LLMChain):
    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        # llm_alt = ChatLiteLLM(temperature=0, model_name="groq/llama3-70b-8192", api_key=os.getenv("GROQ_API_KEY", ""))
        # llm_alt = ChatLiteLLM(temperature=0, model_name="claude-3-opus-20240229", api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        # llm_alt = ChatLiteLLM(temperature=0, model_name="together_ai/meta-llama/Llama-3-70b-chat-hf", api_key="b39a51c976619c8f1e44718c5a0edb7e1780a51ad44667e78931dbe65a2cfb9d")
        
        prompt = PromptTemplate(
            template=EMPATHY_STATEMENT_PROMPT,
            input_variables=[
                "conversation_history", 
                "client_name",
                "human_response", 
                "agent_response",
            ],
        )
        return cls(prompt=prompt, llm=llm, verbose=verbose)



class GoalCompletenessChain(LLMChain):
    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        # llm_alt = ChatLiteLLM(temperature=0, model_name="claude-3-opus-20240229", api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        # llm_alt = ChatLiteLLM(temperature=0, model_name="together_ai/meta-llama/Llama-3-70b-chat-hf", api_key="b39a51c976619c8f1e44718c5a0edb7e1780a51ad44667e78931dbe65a2cfb9d")
        
        prompt = PromptTemplate(
            template=GOAL_COMPLETENESS_STATUS_PROMPT,
            input_variables=[
                "client_name",
                "conversation_history",
                "current_conversation_stage",
            ],
        )
        return cls(prompt=prompt, llm=llm, verbose=verbose)


class SpecificContextChain(LLMChain):
    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        prompt = PromptTemplate(
            template=SPECIFIC_CONTEXT_PROMPT,
            input_variables=[
                "conversation_history",
                "client_name",
                "client_product_summary",
                "human_response",
                "current_conversation_stage",
            ],
        )
        return cls(prompt=prompt, llm=llm, verbose=verbose)


# @time_logger
class CurrentGoalReviewChain(LLMChain):
    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        prompt = PromptTemplate(
            template=CURRENT_GOAL_REVIEW_PROMPT,
            input_variables=[
                "conversation_history",
                "client_name", 
                "current_conversation_stage",
                "goal_completeness_status",
                "interviewee_name",
            ],
        )
        return cls(prompt=prompt, llm=llm, verbose=verbose)



class StageAnalyzerChain(LLMChain):
    """Chain to analyze which conversation stage should the conversation move into."""

    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        """Get the response parser."""
        prompt = PromptTemplate(
            template=STAGE_ANALYZER_PROMPT,
            input_variables=[
                "conversation_history",
                "conversation_stage_id",
                "conversation_stages",
                "conversation_summary",
                "interviewee_type",
                "interviewee_name",
                "goal_completeness_status",
                "question_count_summary",
            ],
        )
        # print(f"STAGE ANALYZER PROMPT {prompt}")
        return cls(prompt=prompt, llm=llm, verbose=verbose)


class QuestionCountChain(LLMChain):
    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        prompt = PromptTemplate(
            template=QUESTION_COUNT_PROMPT,
            input_variables=[
                "conversation_history",
                "client_name",
                "conversation_stage_id",
                "interviewee_name",
                "lead_interviewer",
                "goal_target_question_counts",
                "stage_counts",
            ],
        )
        return cls(prompt=prompt, llm=llm, verbose=verbose)


class TransitionChain(LLMChain):
    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        prompt = PromptTemplate(
            template=TRANSITION_PROMPT,
            input_variables=[
                "interviewee_name",
                "has_progressed",
                "current_conversation_stage",
                "client_name",
                "lead_interviewer",
            ],
        )
        return cls(prompt=prompt, llm=llm, verbose=verbose)

