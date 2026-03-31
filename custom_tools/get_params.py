import json
import re
import frontmatter
import os
from datetime import datetime
from pathlib import Path
from langchain_core.messages import AIMessage

from config import config

user_prompt_path = config.USER_PROMPT_PATH
USER_path = config.MEMORY_PATH / "USER.md"
required_skill_path = config.SKILL_PATH

skill_keys = ["memory"]

def get_skill(skill_type) -> str:
    skill_type = skill_type[0]

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

def get_action(msg):
    action_pattern = r"Action:\s*(.*?)\s*\n"
    action_match = re.search(action_pattern, msg)
    if action_match:
        action = action_match.group(1)
    else:
        action = "None"

    input_pattern = r"```(?:json)?\s*(\{[\s\S]*?\})\s*```"
    input_match = re.search(input_pattern, msg)
    if input_match:
        action_input_str = input_match.group(1)
        input_dict = json.loads(action_input_str)
        input_list = list(input_dict.values())
    else:
        input_list = None
    return action, input_list

def try_getting_final_answer(msg):
    final_pattern = r"Final Answer:\s*(.*)"
    match = re.search(final_pattern, msg, re.DOTALL)

    if match:
        final_answer = match.group(1).strip()  # 提取并去除首尾多余空白
        return final_answer
    else:
        return "[INFO] Continue."

def get_content_and_metadata(reply):
    content = reply.content
    usage_metadata = reply.usage_metadata
    if content == "":
        print(reply)
        print("[WARN] No content.")
    if usage_metadata == "":
        print("[WARN] No usage_metadata.")
    return content, usage_metadata

def print_used_tokens(token_dict):
    input_tokens = token_dict["input_tokens"]
    output_tokens = token_dict["output_tokens"]
    total_tokens = token_dict["total_tokens"]
    token_str = f"Input Tokens: {input_tokens}, Output Tokens: {output_tokens}, Total Tokens: {total_tokens}"
    print(token_str)

def extract_metadata(file_path):
    """
    Extracts YAML front matter from a Markdown file.

    Args:
        file_path (str): Path to the markdown file.

    Returns:
        dict: A dictionary containing the metadata.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If the file format is invalid or missing front matter.
    """

    # Check if the file exists before attempting to open it
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Error: The file '{file_path}' was not found.")

    try:
        # Load the post object which contains both metadata and content
        post = frontmatter.load(file_path)

        # Verify that metadata actually exists (some files might have no front matter)
        if not post.metadata:
            raise ValueError("Warning: No front matter metadata found in this file.")

        return post.metadata

    except Exception as e:
        # Catch any unexpected parsing errors or IO issues
        raise RuntimeError(f"Error: Failed to parse the file '{file_path}'. Details: {str(e)}")

def get_skills_introduction():
    skill_folder_path = config.SKILL_PATH
    skills_introduction = []
    for item in skill_folder_path.iterdir():
        if item.is_dir():
            skill_path = skill_folder_path / item / "SKILL.md"
            skills_introduction.append(extract_metadata(skill_path))
    return skills_introduction
