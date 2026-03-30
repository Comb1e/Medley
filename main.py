import os
from config import config
os.environ["DASHSCOPE_API_KEY"] = config.DASHSCOPE_API_KEY

from custom_tools.tools import tools
from custom_tools.verification import check_env_vars
from custom_tools.run_code import check_and_install_packages, execute_python_code
from custom_tools.get_params import get_user_prompt

from small_agents.agent_template import agent
from small_agents.summarize import MemorySummarizer

BASE_REQUIRED_ENV_VARS = [
    'BASE_AGENT_NAME',
]
check_env_vars(BASE_REQUIRED_ENV_VARS)

BASE_SKILL_PATHS = [
    config.SKILL_PATH / "BASE.md"
]

if __name__ == "__main__":
    summarizer = MemorySummarizer()
    summarizer.run()
    base_agent = agent(
        skill_paths = BASE_SKILL_PATHS,
        type = "base",
        tools = tools,
        enable_memory=True,
        model_name = config.BASE_AGENT_NAME,
        temperature = 0,
    )
    while True:
        user_input = input("You: ").strip()
        if user_input == "quit":
            break
        elif user_input == "read":
            user_input = get_user_prompt()
        final_answer = base_agent.invoke(user_input)
        print("[ANS] " + final_answer)
    base_agent.save_memory_in_queue()

