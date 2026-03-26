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
def generate_or_fix_code(input_raw):
    result_list = [False, "", []]
    try:
        input = ast.literal_eval(input_raw)
    except:
        print(input_raw)
        result_list[1] = "Invalid input format. Please provide a valid list of [json_dir, code_dir]."
        return result_list

    error_msg = is_valid_windows_path_format(input[0])
    if error_msg[0] == False:
        print(input_raw)
        result_list[1] = "Invalid file path. Please provide a valid file path that does not contain illegal characters or reserved names.\n" + error_msg[1]
        return result_list
    json_path = input[0]

    if input[1] != "":
        error_msg = is_valid_windows_path_format(input[1])
        if error_msg[0] == False:
            print(input_raw)
            result_list[1] = "Invalid file path. Please provide a valid file path that does not contain illegal characters or reserved names.\n" + error_msg[1]
            return result_list
        code_path = input[1]
        try:
            with open(code_path, 'r', encoding='utf-8') as file:
                other = file.read()
        except:
            result_list[1] = "The second input is invalid."
            return result_list
    else:
        other = ""

    coding_llm = llm(
        json_path = json_path,
        skill_paths = CODING_SKILL_PATHS,
        type = "coding",
        other = other,
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
        error_msg = is_valid_windows_path_format(str(file_paths / key))
        if error_msg[0] == False:
            print(file_paths / key)
            result_list[1] = "The prompt is inaccurate. Regenerate the prompt and use this tool\n" + error_msg[1]
            return result_list
        result_list[2].append(file_paths / key)
        create_file(file_paths / key, result_dict[key])
    result_list[0] = True
    result_list[1] = "Success."
    return result_list

generate_or_fix_code.name = "generate_or_fix_code"
generate_or_fix_code.description = (
    "# Must use get_prompt(raw_prompt) tool to generate the prompt parameters. #"
    "Create a file in the specified location on the computer and write code. Or fix code in the specified location."
    "The input is a list containing two items."
    "The first is a string containing the path of the JSON file with the prompt parameter."
    "The second is a string containing the path of the code to get fixed. If the task is to generate, leave it empty."
    "The output is a list containing three items."
    "The first is a boolean argument indicating whether the code is generated successfully, true for success."
    "The second is a string contains error message, empty while no error."
    "The third is an array containing multiple items, each is the path to the code file just generated ."
)
generate_or_fix_code.input = {
    "json_dir": str,
    "code_dir": str
}
generate_or_fix_code.output = {
    "is_success": bool,
    "error_message": str,
    "file_paths": [str, str, ...],
}
