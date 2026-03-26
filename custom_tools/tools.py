from langchain.tools import Tool
from custom_tools.create_proj import create_folder
from custom_tools.run_code import check_and_install_packages, execute_python_code
from custom_tools.get_code import get_code, get_files_in_folder

from small_agents.text_related import text_related_generation
from small_agents.prompt import get_prompt

# ====== define tools ======
# tool list
tools = [
    Tool(
        name=create_folder.name,
        func=create_folder,
        description=create_folder.description,
        input=create_folder.input,
        output=create_folder.output
    ),
    Tool(
        name=get_files_in_folder.name,
        func=get_files_in_folder,
        description=get_files_in_folder.description,
        input=get_files_in_folder.input,
        output=get_files_in_folder.output
    ),

    Tool(
        name=text_related_generation.name,
        func=text_related_generation,
        description=text_related_generation.description,
        input=text_related_generation.input,
        output=text_related_generation.output
    ),
    Tool(
        name=get_prompt.name,
        func=get_prompt,
        description=get_prompt.description,
        input=get_prompt.input,
        output=get_prompt.output
    )
]

'''
    Tool(
        name=check_and_install_packages.name,
        func=check_and_install_packages,
        description=check_and_install_packages.description,
        input=check_and_install_packages.input,
        output=check_and_install_packages.output
    ),
    Tool(
        name=execute_python_code.name,
        func=execute_python_code,
        description=execute_python_code.description,
        input=execute_python_code.input,
        output=execute_python_code.output
    ),
    Tool(
        name=get_code.name,
        func=get_code,
        description=get_code.description,
        input=get_code.input,
        output=get_code.output
    ),
'''