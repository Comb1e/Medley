from langchain_community.chat_models import ChatTongyi  # 或 OpenAI, Ollama 等
from langchain_core.prompts import PromptTemplate
import os
import json
import ast

from custom_tools.verification import is_valid_windows_path_format
from custom_tools.read_json import get_llm_prewrite_params
from custom_tools.template import llm_template
from custom_tools.create_proj import create_file

from small_agents.llm_template import llm

CODING_SKILL_PATH = "E:/Projects/Agent/skills/CODING.md"

# ====== use LLM to get image =====
def text2image(input_raw):
    if is_valid_windows_path_format(input_raw) == False:
        print(input_raw)
        raise ValueError("Invalid file path. Please provide a valid file path that does not contain illegal characters or reserved names.")

    json_path = input_raw
    text2image_llm = llm(
        json_path = json_path,
        skill_path = CODING_SKILL_PATH,
        type = "text2image",
        model_name = "qwen-image-plus",
        temperature = 0
    )
    result = coding_llm.invoke()

    try:
        result_dict = ast.literal_eval(result)
    except:
        print(result)
        raise ValueError("Invalid input format. Please provide a valid list of {file_path, code}.")

    file_paths = []
    for key in result_dict.keys():
        if is_valid_windows_path_format(key) == False:
            print(key)
            raise ValueError("Invalid file path. Please provide a valid file path that does not contain illegal characters or reserved names.")
        file_paths.append(key)
        create_file(key, result_dict[key])
    return file_paths

generate_code.name = "generate_code"
generate_code.description = (
    "#Must use get_prompt(raw_prompt) tool to generate the prompt parameters and save them in a JSON file. Then input the file path of the JSON file to this tool to generate code.#"
    "#Must use this tool when you need code.#"
    "#If the code is excutable, excute it after generating to ensure correctness of the code#"
    "Create a file in the specified location on the computer and write code."
    "The input is a string containing the path of the JSON file with the prompt parameter."
    "The output is an array containing multiple items, each is the path to the code file just generated ."
)
generate_code.input = {
    "file_dir": str
}
generate_code.output = {
    "file_paths": [str, str, ...],
}

#todo: add code fixing tool
def fix_code(input_raw):
    return