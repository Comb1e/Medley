import os

from custom_tools.run_code import check_and_install_packages, execute_python_code
if __name__ == "__main__":
    check_and_install_packages("[('python-dotenv', 'dotenv')]")

from config import config
os.environ["DASHSCOPE_API_KEY"] = config.DASHSCOPE_API_KEY


from custom_tools.tools import tools
from custom_tools.verification import check_env_vars

from small_agents.agent_template import agent
from small_agents.prompt import get_prompt
from small_agents.coding import generate_code

BASE_REQUIRED_ENV_VARS = [
    'DASHSCOPE_API_KEY',
    'BASE_AGENT_NAME',
]
check_env_vars(BASE_REQUIRED_ENV_VARS)

BASE_SKILL_PATHS = [
    config.BASE_SKILL_PATH
]
base_agent = agent(
    #json_path = base_prompt_params_path,
    raw_prompt = "写一份识别发绿光物体形状的python代码",
    skill_paths = BASE_SKILL_PATHS,
    type = "base",
    tools = tools,
    model_name = config.BASE_AGENT_NAME,
    temperature = 0,
)

if __name__ == "__main__":
    result = base_agent.invoke()
    print(result)
