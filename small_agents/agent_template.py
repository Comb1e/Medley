import os
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
import json

from pathlib import Path

from custom_tools.get_params import get_skills, get_agent_params, get_USER, get_date_by_today
from custom_tools.verification import check_env_vars
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
        max_history=10,
        logs_dir=config.MEMORY_PATH,
        model_name="qwen-plus",
        temperature=0
    ):
        self.final_answer, self.task = get_agent_params(type)
        self.skills = get_skills(skill_paths)
        self.tools = tools
        self.prompt_folder = config.PROMPT_PATH
        self.default_generate_path = config.GENERATE_PATH

        self.max_history = max_history
        self.logs_dir = logs_dir
        self.init_memory()

        self.chat = ChatOpenAI(
            openai_api_key=config.DASHSCOPE_API_KEY,
            base_url=config.DASHSCOPE_BASE_URL,
            model=model_name,
            temperature=0,
        )
        self.agent = create_react_agent(self.chat, self.tools, agent_prompt_template)
        self.agent_excuator = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True, handle_parsing_errors=True)

    def init_memory(self):
        self.in_memory = InMemory(
            max_history=self.max_history,
            logs_dir=self.logs_dir
        )

    def save_message(self, user_input, reply):
        self.in_memory.store(user_input, reply)
        self.in_memory.flush_session_history()

    def load_memory(self, user_input):
        user = get_USER()
        inMemory = self.in_memory.get_session_history()
        return user, inMemory

    def save_memory_in_queue(self):
        self.in_memory.flush_all_memories()

    def invoke(self, user_input: str):
        self.user, self.inMemory = self.load_memory(user_input)
        reply = self.agent_excuator.invoke({
            "user": self.user,
            "date": get_date_by_today(),
            "in_memory": self.inMemory,
            "raw_prompt": user_input,
            "skills": self.skills,
            "task": self.task,
            "prompt_folder": self.prompt_folder,
            "default_generate_path": self.default_generate_path,
            "final_answer": self.final_answer,
        })["output"]
        self.save_message(user_input, reply)
        return reply
