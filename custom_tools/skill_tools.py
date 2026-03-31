from langchain_core.tools import Tool

from skills.MEMORY.scripts.get_memory import load_memories_from_dates, get_relevant_memory

MEMORY_TOOL = [
    Tool(
        name=load_memories_from_dates.name,
        func=load_memories_from_dates,
        description=load_memories_from_dates.description,
    ),
    Tool(
        name=get_relevant_memory.name,
        func=get_relevant_memory,
        description=get_relevant_memory.description,
    )
]

def add_tools(tools: list,key: str):
    add_tool_list = []
    if key == "memory":
        add_tool_list = MEMORY_TOOL
    else:
        add_tool_list = []
    for add_tool in add_tool_list:
        tools.append(add_tool)
    return tools