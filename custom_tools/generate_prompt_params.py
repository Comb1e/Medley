import ast
import json
from config import config
from custom_tools.verification import is_valid_folder_file_name

def generate_prompt_params(input_raw):
    result_list = [False, "", ""]
    try:
        input = ast.literal_eval(input_raw)
    except:
        print(input_raw)
        result_list[1] = "Invalid input format. Please provide a valid list of [file_name, type, background, purpose, style, tone, audience]."
        return result_list

    error_msg = is_valid_folder_file_name(input[0])
    if error_msg[0] == False:
        print(input[0])
        result_list[1] = "Invalid file name. Please provide a valid file name that does not contain illegal characters or reserved names.\n" + error_msg[1]
        return result_list

    file_name = input[0]
    data = {
        "type": input[1],
        "background": input[2],
        "purpose": input[3],
        "style": input[4],
        "tone": input[5],
        "audience": input[6],
        "folder_name": input[7],
        "path": input[8]
    }

    path = config.PROMPT_PATH / file_name
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except:
        result_list[1] = "Failed to create the json file. Please check if the file path is correct and try again."
        return result_list

    result_list[0] = True
    result_list[1] = "Prompt parameters generated successfully."
    result_list[2] = path
    return result_list


generate_prompt_params.name = "generate_prompt_params"
generate_prompt_params.description = (
    f"Generate prompt params as a json file in {config.PROMPT_PATH} on the computer"
    "The input is an array containing the following nine parameters in order. Each is a string, including file name, type, background, purpose, style, tone, audience, folder name, path."
    f"# Attention # If the user did not specify the path, fill it with {config.GENERATE_PATH}."
    "The output is a list containing three items. The first is a boolean argument indicating whether the folder is successfully created. If failed, do the action again. The second is a string contains error message, empty while no error. The third is a string indicating the location of the json file."
)
generate_prompt_params.input = {
    "file_name": str,
    "type": str,
    "background": str,
    "purpose": str,
    "output_sytle": str,
    "tone": str,
    "audience": str,
    "Path": str
}
generate_prompt_params.output = {
    "is_success": bool,
    "error_message": str,
    "prompt_json_path": str,
}