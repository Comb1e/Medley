import ast
import re
import os
from pathlib import Path

from custom_tools.verification import is_valid_windows_path_format, is_valid_folder_file_name

language_suffixs = {
    r".cpp": "c++",
    r".py": "python",
    r".js": "javascript",
    r".css": "css",
    r".json": "json"
}

def get_files_in_folder(input):
    base_dir = Path(input[0])

    # 获取所有文件名（仅文件，不含子目录）
    files = [f for f in os.listdir(base_dir)
         if os.path.isfile(os.path.join(base_dir, f))]

    return files

get_files_in_folder.name = "get_files_in_folder"
get_files_in_folder.description = (
    "Get all file names under the specified path"
    "The input is an array containing one item, including folder address."
    "The output is an array containing multiple items, including all the name of the files in the folder."
)
get_files_in_folder.input = {
    "base_dir": str,
}
get_files_in_folder.output = {
    "file1": str,
    "file2": str,
    "...": str,
}

def get_code(input_raw) -> [bool, str, str, str]:
    result_list = [False, "", "", ""]
    try:
        input = ast.literal_eval(input_raw)
    except:
        print(input_raw)
        result_list[1] = "Invalid input format. Please provide a valid list of [base_dir, file_name]."
        return result_list

    error_msg = is_valid_windows_path_format(input[0])
    if error_msg[0] == False:
        print(input[0])
        result_list[1] = "Invalid folder address format. Please provide a valid Windows path.\n" + error_msg[1]
        return result_list

    error_msg = is_valid_folder_file_name(input[1])
    if error_msg[0] == False:
        print(input[1])
        result_list[1] = "Invalid file name. Please provide a valid file name that does not contain illegal characters or reserved names.\n" + error_msg[1]
        return result_list

    base_dir = input[0]
    file_name = input[1]
    output = ["", ""]

    match = None
    for language_suffix in language_suffixs.keys():
        match = re.search(language_suffix, file_name, re.IGNORECASE)
        if match != None:
            output[0] = language_suffixs.get(match.group())
            print(f"\nTarget language is {output[0]}")
            break
    if match == None:
        output[0] = "default"

    with open(base_dir + '/' + file_name, 'r', encoding='utf-8') as file:
        output[1] = file.read()

    return output

get_code.name = "get_code"
get_code.description = (
    "Get code in the specified location on the computer"
    "The input is an array containing two items, including file address, file name in order."
    "The output is an array containing four items."
    "The first is a boolean argument indicating whether the code is generated successfully, true for success."
    "The second is a string contains error message, empty while no error."
    "The third is language type"
    "The fourth is all the code in the file."
)
get_code.input = {
    "base_dir": str,
    "file_name": str,
}
get_code.output = {
    "is_success": bool,
    "error_message": str,
    "language_type": str,
    "code": str,
}

if __name__ == "__main__":
    #get_code(r"['E:\Projects\Agent\easy_code\custom_tools', 'get_code.py']")
    get_files_in_folder(r"['E:\Projects\Agent\easy_code\custom_tools']")