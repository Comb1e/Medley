import os
from config import config
os.environ["DASHSCOPE_API_KEY"] = config.DASHSCOPE_API_KEY

from custom_tools.tools import tools
from custom_tools.verification import check_env_vars
from custom_tools.run_code import check_and_install_packages, execute_python_code

from small_agents.agent_template import agent

BASE_REQUIRED_ENV_VARS = [
    'DASHSCOPE_API_KEY',
    'BASE_AGENT_NAME',
]
check_env_vars(BASE_REQUIRED_ENV_VARS)

BASE_SKILL_PATHS = [
    config.BASE_SKILL_PATH
]
base_agent = agent(
    raw_prompt = "Tell me your Memory",
    skill_paths = BASE_SKILL_PATHS,
    type = "base",
    tools = tools,
    enable_memory = True,
    model_name = config.BASE_AGENT_NAME,
    temperature = 0,
)

if __name__ == "__main__":
    result = base_agent.invoke()
    print(result)
