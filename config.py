from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv(".env.local", override=True)

class config:
    ROOT_DIR = Path(__file__).resolve().parent
    SKILL_PATH = ROOT_DIR / "skills"
    BASE_SKILL_PATH = SKILL_PATH / "BASE.md"
    CODING_SKILL_PATH = SKILL_PATH / "CODING.md"
    PROMPT_SKILL_PATH = SKILL_PATH / "PROMPT.md"

    PROMPT_PARAMS_PATH = ROOT_DIR / "prompt_params"
    FINAL_ANSWER_PATH = PROMPT_PARAMS_PATH / "final_answer.json"
    TASK_PATH = PROMPT_PARAMS_PATH / "task.json"

    LOG_PATH = ROOT_DIR / "logs"
    PROMPT_PATH = LOG_PATH / "prompts"
    GENERATE_PATH = LOG_PATH / "generated_files"

    MEMORY_PATH = ROOT_DIR / "memory"
    MEMORY_LOGS_PATH = MEMORY_PATH / "logs"

    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

    BASE_AGENT_NAME = os.getenv("BASE_AGENT_NAME")
    PROMPT_AGENT_NAME = os.getenv("PROMPT_AGENT_NAME")
    CODING_MODEL_NAME = os.getenv("CODING_MODEL_NAME")

if __name__ == "__main__":
    print(config.BASE_SKILL_PATH)
    print(config.DASHSCOPE_API_KEY)