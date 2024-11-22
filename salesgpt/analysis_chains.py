import replicate
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatLiteLLM
import litellm  # Add this import
# litellm.drop_params = True  # Add this line near the top of the file
import os

from .churn_analysis_prompts.analysis_output import ANALYSIS_OUTPUT_PROMPT
from .churn_analysis_prompts.part01_output_parser import PART01_OUTPUT_PARSER_PROMPT
from .churn_analysis_prompts.part02_output_parser import PART02_OUTPUT_PARSER_PROMPT
from .churn_analysis_prompts.part03_output_parser import PART03_OUTPUT_PARSER_PROMPT
from .churn_analysis_prompts.part04_output_parser import PART04_OUTPUT_PARSER_PROMPT
from .churn_analysis_prompts.part05_output_parser import PART05_OUTPUT_PARSER_PROMPT
from .churn_analysis_prompts.part06_output_parser import PART06_OUTPUT_PARSER_PROMPT

ChatLiteLLM.set_verbose = True
litellm.set_verbose=True

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

class AnalysisOutputChain(TracedLLMChain):
    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        llm_analysis = ChatLiteLLM(
            temperature=0, 
            model_name="o1-preview", #o1-preview
            # model_name="gpt-4o-2024-08-06", #o1-preview
            api_key=os.getenv("OPENAI_API_KEY", ""), 
            max_completion_tokens=10000
        )

        prompt = PromptTemplate(
            template=ANALYSIS_OUTPUT_PROMPT,
            input_variables=[
                "conversation_history_raw",
                "client_company_description",
                "agent_name",
                "interviewee_name",
                "unique_customer_identifier",
                "interview_first_name",
                "client_name"
            ],
        )
        return cls(prompt=prompt, llm=llm_analysis, verbose=verbose)

class Part01OutputParserChain(TracedLLMChain):
    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        llm_parser = ChatLiteLLM(
            temperature=0, 
            model_name="gpt-4o-mini", 
            api_key=os.getenv("OPENAI_API_KEY", ""), 
            max_completion_tokens=4000
        )

        prompt = PromptTemplate(
            template=PART01_OUTPUT_PARSER_PROMPT,
            input_variables=["analysis_output"],
        )
        return cls(prompt=prompt, llm=llm_parser, verbose=verbose)

class Part02OutputParserChain(TracedLLMChain):
    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        llm_parser = ChatLiteLLM(
            temperature=0, 
            model_name="gpt-4o-mini", 
            api_key=os.getenv("OPENAI_API_KEY", ""), 
            max_completion_tokens=4000
        )

        prompt = PromptTemplate(
            template=PART02_OUTPUT_PARSER_PROMPT,
            input_variables=["analysis_output"],
        )
        return cls(prompt=prompt, llm=llm_parser, verbose=verbose)

class Part03OutputParserChain(TracedLLMChain):
    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        llm_parser = ChatLiteLLM(
            temperature=0, 
            model_name="gpt-4o-mini", 
            api_key=os.getenv("OPENAI_API_KEY", ""), 
            max_completion_tokens=4000
        )

        prompt = PromptTemplate(
            template=PART03_OUTPUT_PARSER_PROMPT,
            input_variables=["analysis_output"],
        )
        return cls(prompt=prompt, llm=llm_parser, verbose=verbose)

class Part04OutputParserChain(TracedLLMChain):
    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        llm_parser = ChatLiteLLM(
            temperature=0, 
            model_name="gpt-4o-mini", 
            api_key=os.getenv("OPENAI_API_KEY", ""), 
            max_completion_tokens=4000
        )

        prompt = PromptTemplate(
            template=PART04_OUTPUT_PARSER_PROMPT,
            input_variables=["analysis_output"],
        )
        return cls(prompt=prompt, llm=llm_parser, verbose=verbose)

class Part05OutputParserChain(TracedLLMChain):
    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        llm_parser = ChatLiteLLM(
            temperature=0, 
            model_name="gpt-4o-mini", 
            api_key=os.getenv("OPENAI_API_KEY", ""), 
            max_completion_tokens=4000
        )

        prompt = PromptTemplate(
            template=PART05_OUTPUT_PARSER_PROMPT,
            input_variables=["analysis_output"],
        )
        return cls(prompt=prompt, llm=llm_parser, verbose=verbose)

class Part06OutputParserChain(TracedLLMChain):
    @classmethod
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False) -> LLMChain:
        llm_parser = ChatLiteLLM(
            temperature=0, 
            model_name="gpt-4o-mini", 
            api_key=os.getenv("OPENAI_API_KEY", ""), 
            max_completion_tokens=4000
        )

        prompt = PromptTemplate(
            template=PART06_OUTPUT_PARSER_PROMPT,
            input_variables=["analysis_output"],
        )
        return cls(prompt=prompt, llm=llm_parser, verbose=verbose)