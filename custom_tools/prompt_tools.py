from langchain.tools import Tool
from custom_tools.generate_prompt_params import generate_prompt_params
from custom_tools.get_code import get_files_in_folder

prompt_tools = [
    Tool(
        name=generate_prompt_params.name,
        func=generate_prompt_params,
        description=generate_prompt_params.description,
        input=generate_prompt_params.input,
        output=generate_prompt_params.output
    ),
    Tool(
        name=get_files_in_folder.name,
        func=get_files_in_folder,
        description=get_files_in_folder.description,
        input=get_files_in_folder.input,
        output=get_files_in_folder.output
    ),
]