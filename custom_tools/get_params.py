import json
from config import config

final_answer_path = config.FINAL_ANSWER_PATH
task_path = config.TASK_PATH
user_prompt_path = config.USER_PROMPT_PATH
USER_path = config.MEMORY_LOGS_PATH / "USER.md"

def get_final_answer(type):
    with open(final_answer_path, "r", encoding="utf-8") as f:
        final_answer = json.load(f)
    return final_answer[type]

def get_task(type):
    with open(task_path, "r", encoding="utf-8") as f:
        task = json.load(f)
    return task[type]

def get_agent_params(type):
    return get_final_answer(type), get_task(type)

def get_agent_template_params(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        prompt_params = json.load(f)
    return prompt_params

def get_skills(skill_paths):
    skills = ""
    for skill_path in skill_paths:
        with open(skill_path, "r", encoding="utf-8") as f:
            skills += f.read()
    return skills

def get_user_prompt():
    with open(user_prompt_path, "r", encoding="utf-8") as f:
        user_prompt = f.read()
    return user_prompt

def get_USER():
    with open(USER_path, "r", encoding="utf-8") as f:
        user_prompt = f.read()
    return user_prompt