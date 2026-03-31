import importlib
from langchain_core.tools import Tool

from config import config

def add_tools(tools: list, skills_introduction: list, key: str):
    for skill_dict in skills_introduction:
        if skill_dict.get('key') == key:
            name = skill_dict['name']
            func_dict = skill_dict['func']
            for py_path in func_dict:
                funcs = func_dict[py_path]
                for function in funcs:
                    module_path = f"skills.{name}.scripts.{py_path}"
                    module = importlib.import_module(module_path)
                    if hasattr(module, function):
                        target_function = getattr(module, function)
                        print(f"[INFO] Successfully imported {function} from {module_path}")
                        tools.append(
                            Tool(
                            name=function,
                            func=target_function,
                            description=skill_dict['description'],
                        ))
                        print(tools)
                    else:
                        print(f"[Error] Function '{function}' not found in module '{module_path}'.")
    return tools