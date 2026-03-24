from config import config

from custom_tools.prompt_tools import prompt_tools
from custom_tools.verification import check_env_vars

from small_agents.agent_template import prompt_agent

PROMPT_REQUIRED_ENV_VARS = [
    "PROMPT_AGENT_NAME",
]
check_env_vars(PROMPT_REQUIRED_ENV_VARS)

PROMPT_SKILL_PATHS = [
    config.PROMPT_SKILL_PATH
]

# ====== get_prompt ======
def get_prompt(raw_prompt):
    get_prompt_agent = prompt_agent(
        raw_prompt = raw_prompt,
        skill_paths = PROMPT_SKILL_PATHS,
        tools = prompt_tools,
        temperature = 0
    )
    prompt_params_path = get_prompt_agent.invoke()
    return prompt_params_path
get_prompt.name = "get_prompt"
get_prompt.description = (
    "Optimize the raw_prompt to get a more structured prompt that is more conducive to LLM use, and put it in a JSON file in a specific location."
    "The input is a string containing a string which contains the raw_input."
    "The output is a string containing the path to the json file."
)
get_prompt.input = {
    "raw_prompt": str,
}
get_prompt.output = {
    "file_dir": str,
}
