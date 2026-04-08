import os

# ── LangChain core ────────────────────────────────────────────────────────────
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

import json
from pathlib import Path

from custom_tools.get_params import get_skills, get_USER, get_date_by_today, get_action, try_getting_final_answer, get_skills_introduction
from custom_tools.verification import check_env_vars
from custom_tools.skill_tools import add_tools
from custom_tools.rag import retrieve, SemanticSearchEmbeddings, VectorStoreBackend, load_and_chunk_documents, get_vector_store, get_rag_params
from custom_tools.sentence_search import SemanticSearch
from small_agents.prompt_template import llm_prompt_template, agent_prompt_template
from small_agents.in_memory import InMemory
from config import config

REQUIRED_ENV_VARS = [
    'DASHSCOPE_BASE_URL',
    'DASHSCOPE_API_KEY',
]
check_env_vars(REQUIRED_ENV_VARS)

class llm:
    def __init__(self, json_path, skill_paths, error_before, other, project_architecture, model_name="qwen-plus", temperature=0):
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
        self.content = ""
        self.project_architecture = project_architecture
        self.error_before = error_before

        self.chat = ChatOpenAI(
            openai_api_key=config.DASHSCOPE_API_KEY,
            base_url=config.DASHSCOPE_BASE_URL,
            model=model_name,
            temperature=0,
        )
        self.prompt_dict = {
            "error_before": RunnableLambda(lambda x: self.error_before),
            "background": RunnableLambda(lambda x: self.backgournd),
            "purpose": RunnableLambda(lambda x: self.purpose),
            "style": RunnableLambda(lambda x: self.style),
            "tone": RunnableLambda(lambda x: self.tone),
            "audience": RunnableLambda(lambda x: self.audience),
            "skills": RunnableLambda(lambda x: self.skills),
            "other": RunnableLambda(lambda x: self.other),
            "project_architecture": RunnableLambda(lambda x: self.project_architecture)
        }
        self.chain = (
            self.prompt_dict |
            llm_prompt_template |
            self.chat |
            StrOutputParser()
        )

    def invoke(self):
        for token in self.chain.stream({"raw_prompt": ""}):
            print(token, end="", flush=True)
            self.content += token
        return self.content, self.file_paths

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
        self.relevant = ""
        self.ss = SemanticSearch()
        self.embeddings, self.BACKEND, self.vectorstore = get_rag_params(self.ss)

        self.max_history = max_history
        self.logs_dir = logs_dir
        self.enable_memory = enable_memory
        self.init_memory()

        self.chat = ChatOpenAI(
            openai_api_key=config.DASHSCOPE_API_KEY,
            base_url=config.DASHSCOPE_BASE_URL,
            model=model_name,
            streaming=True,
            temperature=0,
        )

    def init_memory(self):
        if self.enable_memory:
            self.in_memory = InMemory(
                ss=self.ss,
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
            print(f"\nTool calling: {action} with input {input}")
            tool = None
            for t in self.tools:
                if t.name == action:
                    if t.name == "get_skill":
                        self.tools = add_tools(self.tools, self.skills_introduction, input[0])
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
        self.relevant = retrieve(user_input, self.vectorstore, self.ss, self.BACKEND)
        self.user, self.inMemory = self.load_memory(user_input)

        for i in range(self.max_iteration):
            self.skills_introduction = get_skills_introduction()
            self.prompt_dict = {
                "root_dir": RunnableLambda(lambda x: config.ROOT_DIR),
                "raw_prompt": RunnablePassthrough(),
                "user": RunnableLambda(lambda x: self.user),
                "context": RunnableLambda(lambda x: self.relevant),
                "iteration": RunnableLambda(lambda x: i),
                "default_prompt_folder": RunnableLambda(lambda x: config.PROMPT_PATH),
                "max_iteration": RunnableLambda(lambda x: self.max_iteration),
                "skills_introduction": RunnableLambda(lambda x: self.skills_introduction),
                "main_distinctions": RunnableLambda(lambda x: self.main_distinctions),
                "date": RunnableLambda(lambda x: get_date_by_today()),
                "in_memory": RunnableLambda(lambda x: self.inMemory),
                "skills": RunnableLambda(lambda x: self.skills),
                "tool_callings": RunnableLambda(lambda x: self.tool_callings),
            }
            self.chain = (
                self.prompt_dict |
                agent_prompt_template |
                self.chat |
                StrOutputParser()
            )
            content = ""
            for token in self.chain.stream({"raw_prompt": user_input}):
                print(token, end="", flush=True)
                content += token
            self.reply += content
            self.tool_calling(content)
            final_answer = try_getting_final_answer(content)
            if final_answer != "[INFO] Continue.":
                break
        self.save_message(user_input, self.reply)
        return final_answer

    def invoke_with_token(self, user_input: str):
        self.relevant = retrieve(user_input, self.vectorstore, self.ss, self.BACKEND)
        self.user, self.inMemory = self.load_memory(user_input)
        for i in range(self.max_iteration):
            self.skills_introduction = get_skills_introduction()
            self.prompt = agent_prompt_template.format(**{
                "root_dir": config.ROOT_DIR,
                "raw_prompt": user_input,
                "user": self.user,
                "context": self.relevant,
                "iteration": i,
                "default_prompt_folder": config.PROMPT_PATH,
                "max_iteration": self.max_iteration,
                "skills_introduction": self.skills_introduction,
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
