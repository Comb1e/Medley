from pathlib import Path
import ast
import re

if __name__ == "__main__":
    from verification import is_valid_windows_path_format, is_valid_folder_file_name
else:
    from custom_tools.verification import is_valid_windows_path_format, is_valid_folder_file_name

def create_folder(input) -> list:
    """Create a folder in the specified location on the computer"""
    result_list = [False, ""]
    error_msg = is_valid_windows_path_format(str(input[0]))
    if error_msg[0] == False:
        print("[INPUT] " + str(input[0]))
        result_list[1] = "[ERROR] Invalid folder address format. Please provide a valid Windows path.\n" + error_msg[1]
        return result_list

    error_msg = is_valid_folder_file_name(str(input[1]))
    if error_msg[0] == False:
        print("[INPUT] " + str(input[1]))
        result_list[1] = "[ERROR] Invalid folder name. Please provide a valid folder name that does not contain illegal characters or reserved names.\n" + error_msg[1]
        return result_list

    base_dir = input[0]
    folder_name = input[1]
    base_path = Path(base_dir)
    new_folder_path = base_path / folder_name
    if new_folder_path.exists():
        result_list[0] = True
        result_list[1] = f"[INFO] Folder {new_folder_path} existed, no need to create."
        return result_list

    new_folder_path.mkdir(parents=True, exist_ok=True)
    result_list[0] = True
    result_list[1] = f"[INFO] Successfully created folder {folder_name} in {base_dir}"
    return result_list

create_folder.name = "create_folder"
create_folder.description = (
    "Create a folder in the specified location on the computer."
    "The input is an array containing two items, folder address and folder name in order."
    "The output is a list containing two items. The first is a boolean argument indicating whether the folder is successfully created. If failed, do the action again. The second is a string contains error message, empty while no error."
)
create_folder.input = {
        "base_dir": str,
        "folder_name": str
}
create_folder.output = {
    "is_success": bool,
    "error_message": str
}

def create_file(file_path, code_block):
    # 提取代码块（兼容 Markdown）
    md_code_block = None
    for language in language_type:
        escaped_language = re.escape(language)
        block = r"```" + escaped_language + r"\n(.*?)\n```"
        md_code_block = re.search(block, code_block, re.DOTALL)
        if md_code_block:
            code = md_code_block.group(1)
            break
    if md_code_block == None:
        # 如果没有代码块，尝试提取所有可能的代码
        code = code_block

    create_folder([file_path.parent.parent, file_path.parent.name])
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(code)

    print(f"\n[INFO] Successfully created file in {file_path}")

language_type = [r"python", r"java", r"css", r"c++", r"javascript", r"go", r"ruby", r"php", r"c#", r"swift", r"kotlin"]

# ====== test ======
if __name__ == "__main__":
    #generate_code([create_folder(["E:/Projects/Python/agent_test", "test"]), "test.txt", "hello"])
    #create_folder("[\"E:/Projects/Python/agent_test\", \"bayesian\"]")
    create_file(
        Path('E:\\Projects\\Agent\\logs\\generated_files\\flappy_bird_project\\flappy_bird.py'),
        "hello"
    )