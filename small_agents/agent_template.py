from langchain_community.chat_models import ChatTongyi  # 或 OpenAI, Ollama 等
from langchain_core.prompts import PromptTemplate
from langchain.agents import create_react_agent, AgentExecutor
import json

from pathlib import Path

from custom_tools.get_params import get_skills, get_final_answer
from custom_tools.prompt_template import llm_prompt_template, prompt_get_prompt_template, agent_prompt_template

from config import config

class llm:
    def __init__(self, json_path, skill_paths, type, model_name="qwen-plus", temperature=0):
        with open(json_path, "r", encoding="utf-8") as f:
            prompt_params = json.load(f)
        self.backgournd = prompt_params["background"]
        self.purpose = prompt_params["purpose"]
        self.style = prompt_params["style"]
        self.tone = prompt_params["tone"]
        self.audience = prompt_params["audience"]
        self.skills =  get_skills(skill_paths)
        self.file_paths = Path(prompt_params["path"]) / prompt_params["folder_name"]

        self.chat = ChatTongyi(model_name=model_name, temperature=temperature)
        self.prompt = llm_prompt_template.format(**{
            "background": self.backgournd,
            "purpose": self.purpose,
            "style": self.style,
            "tone": self.tone,
            "audience": self.audience,
            "skills": self.skills,
        })

    def invoke(self):
        result = self.chat.invoke(self.prompt)
        return result.content, self.file_paths

class prompt_agent:
    def __init__(self, raw_prompt, skill_paths, tools, temperature=0):
        self.raw_prompt = raw_prompt
        self.final_answer = get_final_answer("prompt")
        self.skills = get_skills(skill_paths)
        self.tools = tools

        self.chat = ChatTongyi(model=config.PROMPT_AGENT_NAME, temperature=0)
        self.agent = create_react_agent(self.chat, self.tools, prompt_get_prompt_template)
        self.agent_excuator = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True, handle_parsing_errors=True)

    def invoke(self):
        prompt_params_path = self.agent_excuator.invoke({
            "raw_prompt": self.raw_prompt,
            "skills": self.skills,
            "final_answer": self.final_answer,
        })["output"]
        return prompt_params_path

class agent:
    def __init__(self, json_path, skill_paths, type, tools, model_name="qwen-plus", temperature=0):
        with open(json_path, "r", encoding="utf-8") as f:
            prompt_params = json.load(f)
        self.backgournd = prompt_params["background"]
        self.purpose = prompt_params["purpose"]
        self.style = prompt_params["style"]
        self.tone = prompt_params["tone"]
        self.audience = prompt_params["audience"]
        self.project_path = Path(prompt_params["path"]) / prompt_params["folder_name"]
        self.skills = get_skills(skill_paths)
        self.final_answer = get_final_answer(type)
        self.tools = tools

        self.chat = ChatTongyi(model_name=model_name, temperature=temperature)
        self.agent = create_react_agent(self.chat, self.tools, agent_prompt_template)
        self.agent_excuator = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True, handle_parsing_errors=True)

    def invoke(self):
        result = self.agent_excuator.invoke({
            "background": self.backgournd,
            "purpose": self.purpose,
            "style": self.style,
            "tone": self.tone,
            "audience": self.audience,
            "project_path": self.project_path,
            "skills": self.skills,
            "final_answer": self.final_answer,
        })
        return result["output"]