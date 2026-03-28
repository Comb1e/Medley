import json
from datetime import datetime

from config import config

final_answer_path = config.FINAL_ANSWER_PATH
task_path = config.TASK_PATH
user_prompt_path = config.USER_PROMPT_PATH
USER_path = config.MEMORY_PATH / "USER.md"
required_skill_path = config.SKILL_PATH

skill_keys = ["memory"]

def get_skill(skill_type) -> str:
    path = required_skill_path
    if skill_type == "memory":
        path = path / "MEMORY"
    else:
        return "None"
    path = path / "SKILL.md"
    with open(path, "r", encoding="utf-8") as f:
        skill = f.read()
    print("\n") # Make terminal more readable
    return skill
get_skill.name = "get_skill"
get_skill.description = (
    "Get the required skill."
    f"The input is a string. Only value in {skill_keys} is available"
    "The output is the skill to read"
)
get_skill.input = {
    "skill_type": str,
}
get_skill.output = {
    "skill": str
}

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

def get_date_by_today():
    return datetime.now().isoformat()