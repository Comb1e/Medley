import ast
import json
from config import config

from custom_tools.verification import is_valid_windows_path_format, check_env_vars
from custom_tools.create_proj import create_file

from small_agents.agent_template import llm

TEXTING_REQUIRED_ENV_VARS = [
    'CODING_MODEL_NAME',
    'TEXTING_MODEL_NAME'
]
check_env_vars(TEXTING_REQUIRED_ENV_VARS)

CODING_SKILL_PATHS = [
    config.SKILL_PATH / "TEXT_RELATED.md",
    config.SKILL_PATH / "CODING.md"
]

TEXTING_SKILL_PATHS = [
    config.SKILL_PATH / "TEXT_RELATED.md",
    config.SKILL_PATH / "TEXTING.md"
]

def get_llm_params(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        task_type = json.load(f)["type"]
    if task_type == "coding":
        return CODING_SKILL_PATHS, config.CODING_MODEL_NAME
    elif task_type == "text":
        return TEXTING_SKILL_PATHS, config.TEXTING_MODEL_NAME

# ====== LLM =====
def text_related_generation(input):
    result_list = [False, "", []]
    json_path = input[0]

    if input[1] != "":
        error_msg = is_valid_windows_path_format(input[1])
        if error_msg[0] == False:
            print("[input] " + input)
            result_list[1] = "[ERROR] Invalid file path. Please provide a valid file path that does not contain illegal characters or reserved names.\n" + error_msg[1]
            return result_list
        code_path = input[1]
        try:
            with open(code_path, 'r', encoding='utf-8') as file:
                other = file.read()
        except:
            result_list[1] = "[ERROR] The second input is invalid."
            return result_list
    else:
        other = ""

    llm_skill_paths, llm_model_name = get_llm_params(json_path)
    coding_llm = llm(
        json_path = json_path,
        skill_paths = llm_skill_paths,
        type = "coding",
        other = other,
        model_name = llm_model_name,
        temperature = 0
    )
    result, file_paths = coding_llm.invoke()

    try:
        result_dict = ast.literal_eval(result)
    except:
        print(result)
        result_list[1] = "[ERROR] The prompt is inaccurate. Regenerate the prompt and use this tool."
        return result_list

    for key in result_dict.keys():
        error_msg = is_valid_windows_path_format(str(file_paths / key))
        if error_msg[0] == False:
            print(file_paths / key)
            result_list[1] = "[ERROR] The prompt is inaccurate. Regenerate the prompt and use this tool\n" + error_msg[1]
            return result_list
        result_list[2].append(file_paths / key)
        create_file(file_paths / key, result_dict[key])
    result_list[0] = True
    result_list[1] = "[INFO] Success."
    return result_list

text_related_generation.name = "text_related_generation"
text_related_generation.description = (
    "When need text, whether code or argumentative paper, Use this tool."
    "The input is a list containing two items."
    "The first is a string containing the path of the JSON file with the prompt parameter."
    "The second is a string containing the path of the code to get fixed. If the task is to generate, leave it empty."
    "The output is a list containing three items."
    "The first is a boolean argument indicating whether the code is generated successfully, true for success."
    "The second is a string contains error message, empty while no error."
    "The third is an array containing multiple items, each is the path to the code file just generated ."
)
text_related_generation.input = [
    "json_dir",
    "code_dir"
]

text_related_generation.output = [
    "is_success",
    "error_message",
    "file_paths",
]
