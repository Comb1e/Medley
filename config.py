from dotenv import load_dotenv
import os
from pathlib import Path

os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

load_dotenv(".env.local", override=True)

os.environ["HF_TOKEN"] = os.getenv("HUGGING_FACE_TOKEN")  # for Hugging Face API access, if needed

class config:
    ROOT_DIR = Path(__file__).resolve().parent
    SKILL_PATH = ROOT_DIR / "skills"
    USER_PROMPT_PATH = ROOT_DIR / "user_prompt.md"

    LOG_PATH = ROOT_DIR / "logs"
    PROMPT_PATH = LOG_PATH / "prompts"
    GENERATE_PATH = LOG_PATH / "generated_files"
    MEMORY_PATH = LOG_PATH / "memory"

    DATA_BASE_DIR = ROOT_DIR / "data_base"
    DOCS_DIR = DATA_BASE_DIR / "docs"
    CHROMA_PERSIST_DIR = DATA_BASE_DIR / "chroma_db"
    CHROMA_COLLECTION  = "knowledge_base"

    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
    DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL")

    BASE_AGENT_NAME = os.getenv("BASE_AGENT_NAME")
    PROMPT_AGENT_NAME = os.getenv("PROMPT_AGENT_NAME")
    CODING_MODEL_NAME = os.getenv("CODING_MODEL_NAME")
    TEXTING_MODEL_NAME = os.getenv("TEXTING_MODEL_NAME")
    SUMMARIZING_MODEL_NAME = os.getenv("SUMMARIZING_MODEL_NAME")

    EMBEDDINGS_MODEL_NAME =  os.getenv("EMBEDDINGS_MODEL_NAME")

if __name__ == "__main__":
    print(config.BASE_SKILL_PATH)
    print(config.DASHSCOPE_API_KEY)