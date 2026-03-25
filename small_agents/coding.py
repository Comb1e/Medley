import ast
from config import config

from custom_tools.verification import is_valid_windows_path_format, check_env_vars
from custom_tools.create_proj import create_file

from small_agents.agent_template import llm

CODING_REQUIRED_ENV_VARS = [
    'CODING_MODEL_NAME',
]
check_env_vars(CODING_REQUIRED_ENV_VARS)

CODING_SKILL_PATHS = [
    config.CODING_SKILL_PATH
]

# ====== use LLM for coding =====
def generate_code(input_raw):
    result_list = [False, "", []]
    if is_valid_windows_path_format(input_raw) == False:
        print(input_raw)
        result_list[1] = "Invalid file path. Please provide a valid file path that does not contain illegal characters or reserved names."
        return result_list

    json_path = input_raw
    coding_llm = llm(
        json_path = json_path,
        skill_paths = CODING_SKILL_PATHS,
        type = "coding",
        model_name = config.CODING_MODEL_NAME,
        temperature = 0
    )
    result, file_paths = coding_llm.invoke()

    try:
        result_dict = ast.literal_eval(result)
    except:
        print(result)
        result_list[1] = "The prompt is inaccurate. Regenerate the prompt and use this tool."
        return result_list

    for key in result_dict.keys():
        if is_valid_windows_path_format(file_paths / key) == False:
            print(file_paths / key)
            result_list[1] = "The prompt is inaccurate. Regenerate the prompt and use this tool"
            return result_list
        result_list[2].append(file_paths / key)
        create_file(file_paths / key, result_dict[key])
    result_list[0] = True
    result_list[1] = "Code generated successfully."
    return result_list

generate_code.name = "generate_code"
generate_code.description = (
    "# Must use get_prompt(raw_prompt) tool to generate the prompt parameters. #"
    "# Must use this tool when you need code. #"
    "Create a file in the specified location on the computer and write code."
    "The input is a string containing the path of the JSON file with the prompt parameter."
    "The output is a list containing three items. The first is a boolean argument indicating whether the code is generated successfully, true for success. The second is a string contains error message, empty while no error. The third is an array containing multiple items, each is the path to the code file just generated ."
)
generate_code.input = {
    "file_dir": str
}
generate_code.output = {
    "is_success": bool,
    "error_message": str,
    "file_paths": [str, str, ...],
}

#todo: add code fixing tool
def fix_code(input_raw):
    return