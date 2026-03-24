import json
from config import config

final_answer_path = config.FINAL_ANSWER_PATH

def get_final_answer(type):
    with open(final_answer_path, "r", encoding="utf-8") as f:
        final_answer = json.load(f)
    return final_answer[type]

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