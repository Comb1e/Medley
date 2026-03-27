from langchain_community.chat_models import ChatTongyi  # 或 OpenAI, Ollama 等
from langchain_core.prompts import PromptTemplate
from langchain.agents import create_react_agent, AgentExecutor
import json

from pathlib import Path

from custom_tools.get_params import get_skills, get_agent_params
from small_agents.prompt_template import llm_prompt_template, agent_prompt_template
from memory.in_memory import in_memory
from memory.vector_memory import SemanticAgent
from config import config

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

        self.chat = ChatTongyi(model_name=model_name, temperature=temperature)
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
        self, type, raw_prompt, skill_paths, tools,
        enable_memory=False,
        max_history=6,
        days_to_index=7,
        logs_dir=config.MEMORY_LOGS_PATH,
        model_name="qwen-plus",
        temperature=0
    ):
        self.raw_prompt = raw_prompt
        self.final_answer, self.task = get_agent_params(type)
        self.skills = get_skills(skill_paths)
        self.tools = tools
        self.prompt_folder = config.PROMPT_PATH
        self.default_generate_path = config.GENERATE_PATH

        self.enable_memory = enable_memory
        self.max_history = max_history
        self.days_to_index = days_to_index
        self.logs_dir = logs_dir
        self.init_memory()
        self.inMemory, self.relevant = self.load_momery()

        self.chat = ChatTongyi(model=model_name, temperature=0)
        self.agent = create_react_agent(self.chat, self.tools, agent_prompt_template)
        self.agent_excuator = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True, handle_parsing_errors=True)

    def init_memory(self):
        if self.enable_memory:
            self.in_memory = in_memory(
            max_history=self.max_history,
            logs_dir=self.logs_dir
            )
            self.vector_memory = SemanticAgent(
                days_to_index=self.days_to_index
            )

    def save_message(self, reply):
        if self.enable_memory:
            self.in_memory.store(self.raw_prompt, reply)
            self.vector_memory.store(self.raw_prompt, reply)

    def load_momery(self):
        if self.enable_memory:
            inMemory = self.in_memory.history
            relevant = self.vector_memory.get_relevant(self.raw_prompt, top_k=3)
            print(relevant)
            return inMemory, relevant
        else:
            return "None", "None"

    def invoke(self):
        reply = self.agent_excuator.invoke({
            "days_to_index": self.days_to_index,
            "in_memory": self.inMemory,
            "vector_memory": self.relevant,
            "raw_prompt": self.raw_prompt,
            "skills": self.skills,
            "task": self.task,
            "prompt_folder": self.prompt_folder,
            "default_generate_path": self.default_generate_path,
            "final_answer": self.final_answer,
        })["output"]
        self.save_message(reply)
        return reply
