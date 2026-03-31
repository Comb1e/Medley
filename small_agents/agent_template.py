import os
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
import json
from pathlib import Path

from custom_tools.get_params import get_skills, get_USER, get_date_by_today, get_action, try_getting_final_answer, get_content_and_metadata, print_used_tokens, get_skills_introduction
from custom_tools.verification import check_env_vars
from custom_tools.skill_tools import add_tools
from small_agents.prompt_template import llm_prompt_template, agent_prompt_template
from small_agents.in_memory import InMemory
from config import config

REQUIRED_ENV_VARS = [
    'DASHSCOPE_BASE_URL',
    'DASHSCOPE_API_KEY',
]
check_env_vars(REQUIRED_ENV_VARS)

class llm:
    def __init__(self, json_path, skill_paths, type, other, model_name="qwen-plus", temperature=0):
        with open(json_path, "r", encoding="utf-8") as f:
            prompt_params = json.load(f)
        self.backgournd = prompt_params["background"]
        self.purpose = prompt_params["purpose"]
        self.style = prompt_params["style"]
        self.tone = prompt_params["tone"]
        self.audience = prompt_params["audience"]
        self.skills =  get_skills(skill_paths)
        self.file_paths = Path(prompt_params["path"]) / prompt_params["folder_name"]
        self.other = other

        self.chat = ChatOpenAI(
            openai_api_key=config.DASHSCOPE_API_KEY,
            base_url=config.DASHSCOPE_BASE_URL,
            model=model_name,
            temperature=0,
        )
        self.prompt = llm_prompt_template.format(**{
            "background": self.backgournd,
            "purpose": self.purpose,
            "style": self.style,
            "tone": self.tone,
            "audience": self.audience,
            "skills": self.skills,
            "other": self.other
        })

    def invoke(self):
        result = self.chat.invoke(self.prompt)
        return result.content, self.file_paths

class agent:
    def __init__(
        self, type, skill_paths, tools,
        enable_memory=False,
        max_iteration=5,
        max_history=10,
        logs_dir=config.MEMORY_PATH,
        model_name="qwen-plus",
        main_distinctions="",
        temperature=0
    ):
        self.skills = get_skills(skill_paths)
        self.tools = tools
        self.max_iteration = max_iteration
        self.main_distinctions = main_distinctions
        self.tool_callings = []
        self.reply = ""

        self.max_history = max_history
        self.logs_dir = logs_dir
        self.enable_memory = enable_memory
        self.init_memory()

        self.chat = ChatOpenAI(
            openai_api_key=config.DASHSCOPE_API_KEY,
            base_url=config.DASHSCOPE_BASE_URL,
            model=model_name,
            temperature=0,
        )

    def init_memory(self):
        if self.enable_memory:
            self.in_memory = InMemory(
                max_history=self.max_history,
                logs_dir=self.logs_dir
            )

    def save_message(self, user_input, reply):
        if self.enable_memory:
            self.in_memory.store(user_input, reply)
            self.in_memory.flush_session_history()

    def load_memory(self, user_input):
        user = get_USER()
        if self.enable_memory:
            inMemory = self.in_memory.get_session_history()
            return user, inMemory
        else:
            return user, ""

    def save_memory_in_queue(self):
        self.in_memory.flush_all_memories()

    def tool_calling(self, msg):
        action, input = get_action(msg)
        tool_calling = ""
        if action != "None":
            tool_calling += f"Tool calling: {action} with input {input}; "
            print(f"Tool calling: {action} with input {input}")
            tool = None
            for t in self.tools:
                if t.name == action:
                    if t.name == "get_skill":
                        self.tools = add_tools(self.tools, input[0])
                    tool = t
                    break
            if tool is not None:
                result = tool.func(input)
                tool_calling += f"Tool result: {result}; "
                print(f"Tool result: {result}")
            else:
                tool_calling += f"Tool {action} not found.; "
                print(f"Tool {action} not found.")
        else:
            tool_calling += "No tool calling."
            print("No tool calling.")
        self.tool_callings.append(tool_calling)

    def invoke(self, user_input: str):
        self.user, self.inMemory = self.load_memory(user_input)

        for i in range(self.max_iteration):
            self.prompt = agent_prompt_template.format(**{
                "raw_prompt": user_input,
                "user": self.user,
                "iteration": i,
                "default_prompt_folder": config.PROMPT_PATH,
                "max_iteration": self.max_iteration,
                "skills_introduction": get_skills_introduction(),
                "main_distinctions": self.main_distinctions,
                "date": get_date_by_today(),
                "in_memory": self.inMemory,
                "skills": self.skills,
                "tool_callings": self.tool_callings,
            })
            reply = self.chat.invoke(self.prompt)
            content, metadata = get_content_and_metadata(reply)
            print_used_tokens(metadata)
            self.reply += content
            print(content)
            self.tool_calling(content)
            final_answer = try_getting_final_answer(content)
            if final_answer != "[INFO] Continue.":
                break
        self.save_message(user_input, self.reply)
        return final_answer
