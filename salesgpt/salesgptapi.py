import json
import os
from langchain_community.chat_models import ChatLiteLLM
import asyncio
from salesgpt.agents import SalesGPT
import re
GPT_MODEL = "gpt-3.5-turbo"
# GPT_MODEL = "claude-2"
# GPT_MODEL = "claude-3-haiku-20240307"
# GPT_MODEL = "groq/llama2-70b-4096"
# GPT_MODEL = "groq/mixtral-8x7b-32768"
# GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
# ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


# This initialises the SalesGPT class
# In my current code, I saved a new instance each time the /call endpoint is hit
# So will need to do that and ensure the config pass in works
# This is seemingly also where the model is decided

class SalesGPTAPI:
    USE_TOOLS = False

    def __init__(self, config_path: str, verbose: bool = False, max_num_turns: int = 20,use_tools=False):
        self.config_path = config_path
        self.verbose = verbose
        self.max_num_turns = max_num_turns
        # self.llm = ChatLiteLLM(temperature=0.2, model_name=GPT_MODEL, api_key=ANTHROPIC_API_KEY)
        self.llm = ChatLiteLLM(temperature=0.2, model_name=GPT_MODEL)
        self.conversation_history = []
        self.use_tools = use_tools
        self.sales_agent = self.initialize_agent()
        self.current_turn = 0
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
        print(f"SalesGPT use_tools: {sales_agent.use_tools}")  # Print the use_tools value of the SalesGPT instance
        sales_agent.seed_agent()
        return sales_agent


    # # This do method essentially just runs the standard non-stream response
    # def do(self, human_input=None):
    #     # This code just increments the current turn counter
    #     self.current_turn+=1
    #     current_turns = self.current_turn
    #     if current_turns >= self.max_num_turns:
    #         print("Maximum number of turns reached - ending the conversation.")
    #         return ["BOT","In case you'll have any questions - just text me one more time!"]

    #     #self.sales_agent.seed_agent() why do we seeding at each turn? put to agent_init
    #     #self.sales_agent.conversation_history = conversation_history

    #     # This is not needed as I'll append the human response to the conversation history in my main voice file
    #     if human_input is not None:
    #         self.sales_agent.human_step(human_input)

    #     self.sales_agent.update_conversation_summary()

    #     # Moved this from below
    #     self.sales_agent.determine_conversation_stage()

    #     # This calls the sales agent's step method to generate the next response and updates the conversation stage
    #     ai_log = self.sales_agent.step(stream=False)

    #     # This updates the conversation stage but running the stage analyzer chain 
    #     # Not sure why it's happening here? Can change this
    #     # self.sales_agent.determine_conversation_stage()
        
    #     # This essentially checks whether the last response includes <END_OF_CALL>
    #     # Not needed
    #     if "<END_OF_CALL>" in self.sales_agent.conversation_history[-1]:
    #         print("Sales Agent determined it is time to end the conversation.")
    #         return ["BOT","In case you'll have any questions - just text me one more time!"]

    #     # This gets the last agent response added to the conversation history dictionary
    #     reply = self.sales_agent.conversation_history[-1]

    #     if self.verbose:
    #         print("=" * 10)
    #         print(ai_log)
    #     ''''''
    #     # if ai_log['intermediate_steps'][1]['outputs']['intermediate_steps'] is not []:
    #     #     try:
    #     #         res_str = ai_log['intermediate_steps'][1]['outputs']['intermediate_steps'][0]
    #     #         tool_search_result = res_str[0]
    #     #         agent_action = res_str[0]
    #     #         tool,tool_input,log = agent_action.tool, agent_action.tool_input, agent_action.log
    #     #         actions = re.search(r"Action: (.*?)[\n]*Action Input: (.*)",log)
    #     #         action_input= actions.group(2)
    #     #         action_output = ai_log['intermediate_steps'][1]['outputs']['intermediate_steps'][0][1]
    #     #     except:
    #     #         tool,tool_input,action,action_input,action_output = "","","","",""
    #     # else:   
    #     #     tool,tool_input,action,action_input,action_output = "","","","",""

    #     if self.use_tools and 'intermediate_steps' in ai_log:
    #         try:
    #             res_str = ai_log['intermediate_steps'][1]['outputs']['intermediate_steps'][0]
    #             tool_search_result = res_str[0]
    #             agent_action = res_str[0]
    #             tool, tool_input, log = agent_action.tool, agent_action.tool_input, agent_action.log
    #             actions = re.search(r"Action: (.*?)[\n]*Action Input: (.*)", log)
    #             action_input = actions.group(2)
    #             action_output = ai_log['intermediate_steps'][1]['outputs']['intermediate_steps'][0][1]
    #         except:
    #             tool, tool_input, action, action_input, action_output = "", "", "", "", ""
    #     else:
    #         tool, tool_input, action, action_input, action_output = "", "", "", "", ""
        
    #     # This is a payload dictionary containing details about the bot's response, the conversational stage and any tool usage
    #     print(reply)
    #     payload = {
    #         "bot_name": reply.split(": ")[0],
    #         "response": ': '.join(reply.split(": ")[1:]).rstrip('<END_OF_TURN>'),
    #         "conversational_stage": self.sales_agent.current_conversation_stage,
    #         "tool": tool,
    #         "tool_input": tool_input,
    #         "action_output": action_output,
    #         "action_input": action_input
    #     }
    #     return payload
    

    # This do method essentially just runs the standard non-stream response
    def do(self, conversation_history: list, human_input=None):

        # Update the sales agent's conversation history with the provided conversation_history
        self.sales_agent.conversation_history = conversation_history
        
        # This code just increments the current turn counter
        self.current_turn+=1
        current_turns = self.current_turn
        if current_turns >= self.max_num_turns:
            print("Maximum number of turns reached - ending the conversation.")
            return ["BOT","In case you'll have any questions - just text me one more time!"]

        #self.sales_agent.seed_agent() why do we seeding at each turn? put to agent_init
        #self.sales_agent.conversation_history = conversation_history

        # This is not needed as I'll append the human response to the conversation history in my main voice file
        if human_input is not None:
            self.sales_agent.human_step(human_input)

        self.sales_agent.update_conversation_summary()

        # Moved this from below
        self.sales_agent.determine_conversation_stage()

        # This calls the sales agent's step method to generate the next response and updates the conversation stage
        ai_log = self.sales_agent.step(stream=False)

        # This updates the conversation stage but running the stage analyzer chain 
        # Not sure why it's happening here? Can change this
        # self.sales_agent.determine_conversation_stage()
        
        # This essentially checks whether the last response includes <END_OF_CALL>
        # Not needed
        if "<END_OF_CALL>" in self.sales_agent.conversation_history[-1]:
            print("Sales Agent determined it is time to end the conversation.")
            return ["BOT","In case you'll have any questions - just text me one more time!"]

        # This gets the last agent response added to the conversation history dictionary
        reply = self.sales_agent.conversation_history[-1]

        if self.verbose:
            print("=" * 10)
            print(ai_log)
        ''''''

        if self.use_tools and 'intermediate_steps' in ai_log:
            try:
                res_str = ai_log['intermediate_steps'][1]['outputs']['intermediate_steps'][0]
                tool_search_result = res_str[0]
                agent_action = res_str[0]
                tool, tool_input, log = agent_action.tool, agent_action.tool_input, agent_action.log
                actions = re.search(r"Action: (.*?)[\n]*Action Input: (.*)", log)
                action_input = actions.group(2)
                action_output = ai_log['intermediate_steps'][1]['outputs']['intermediate_steps'][0][1]
            except:
                tool, tool_input, action, action_input, action_output = "", "", "", "", ""
        else:
            tool, tool_input, action, action_input, action_output = "", "", "", "", ""
        
        # This is a payload dictionary containing details about the bot's response, the conversational stage and any tool usage
        print(reply)
        payload = {
            "bot_name": reply.split(": ")[0],
            "response": ': '.join(reply.split(": ")[1:]).rstrip('<END_OF_TURN>'),
            "conversational_stage": self.sales_agent.current_conversation_stage,
            "tool": tool,
            "tool_input": tool_input,
            "action_output": action_output,
            "action_input": action_input
        }
        return payload





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