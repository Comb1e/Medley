from config import config

from custom_tools.prompt_tools import prompt_tools
from custom_tools.verification import check_env_vars

from small_agents.agent_template import agent

PROMPT_REQUIRED_ENV_VARS = [
    "PROMPT_AGENT_NAME",
]
check_env_vars(PROMPT_REQUIRED_ENV_VARS)

PROMPT_SKILL_PATHS = [
    config.SKILL_PATH / "PROMPT.md"
]

# ====== get_prompt ======
def get_prompt(raw_prompt):
    raw_prompt = raw_prompt[0]
    print("[INFO] Generating Prmopt\n")
    get_prompt_agent = agent(
        type = "prompt",
        skill_paths = PROMPT_SKILL_PATHS,
        max_iteration=3,
        model_name = config.PROMPT_AGENT_NAME,
        tools = prompt_tools,
        main_distinctions= f"1. The tool \"get_files_in_folder\" should be use to check the default prompt folder.\n 2. The parameter \"path\" should be the path indicated by the user in #Raw Prompt#. If the user did not indicate one, it should be {config.GENERATE_PATH}.",
        temperature = 0
    )
    prompt_params_path = get_prompt_agent.invoke(raw_prompt)
    return prompt_params_path
get_prompt.name = "get_prompt"
get_prompt.description = (
    "Optimize the raw_prompt to get a more structured prompt that is more conducive to LLM use, and put it in a JSON file in a specific location."
    "The input is a string containing a string which contains the raw_input."
    "The output is a string containing the path to the json file."
)
get_prompt.input = {
    "raw_prompt": str
}
get_prompt.output = {
    "file_dir": str
}
