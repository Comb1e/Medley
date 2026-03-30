import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from config import config
from small_agents.semantic_agent import SemanticAgent

def parse_dates(date_string: list) -> List[datetime]:
    """
    Args:
        date_string (list): Comma-separated string of dates in format 'YYYY-MM-DD'

    Returns:
        List[datetime]: List of parsed datetime objects

    Raises:
        ValueError: If any date in the string is invalid
    """
    for date_str in date_string:
        date_str = date_str.strip()
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            dates.append(date_obj)
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}. Expected format: YYYY-MM-DD")

    return dates

def load_memories_from_dates(date_string: str) -> List[Dict[str, Any]]:
    """
    Load raw memories from specified date folders.

    Args:
        date_string (str): Comma-separated string of dates in format 'YYYY-MM-DD'
        base_path (str): Base directory path where date folders are located

    Returns:
        List[Dict[str, Any]]: List of parsed objects from JSONL files

    Raises:
        FileNotFoundError: If any date folder doesn't exist
        IOError: If there's an issue reading JSONL files
    """
    # Parse dates from string
    dates = parse_dates(date_string)

    # Validate that all folders exist
    base_path = config.MEMORY_PATH
    for date in dates:
        folder_path = os.path.join(base_path, date.strftime('%Y-%m-%d'))
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Folder does not exist: {folder_path}")

    # Collect all parsed objects
    all_objects = []

    # Process each date folder
    for date in dates:
        folder_path = os.path.join(base_path, date.strftime('%Y-%m-%d'))

        # Find all .md files in the folder
        for filename in os.listdir(folder_path):
            if filename.endswith('.md'):
                file_path = os.path.join(folder_path, filename)

                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:  # 跳过空行
                            try:
                                all_objects.append(line)  # 直接添加文本行
                            except Exception as e:
                                raise IOError(f"Error reading {file_path}: {str(e)}")
    return all_objects
load_memories_from_dates.name = "load_memories_from_dates"
load_memories_from_dates.description = "#Must Use get_skill(memory) before deciding to call this tool.#"

def get_relevant_memory(user_input):
    user_input = user_input[0]
    agent = SemanticAgent(need_index=True, days_to_index=7)
    relevant_memory = agent.get_relevant(user_input, top_k=3)
    return f"The relevant conversations in the past seven days are as follows {relevant_memory}"
get_relevant_memory.name = "get_relevant_memory"
get_relevant_memory.description = "#Must Use get_skill(memory) before deciding to call this tool.#"