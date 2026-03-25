import re
import os
from pathlib import PureWindowsPath  # 注意：用 PureWindowsPath，不依赖当前系统

def is_valid_windows_path_format(path: str) -> list:
    """
    Checks if a string is a valid Windows path format.

    Args:
        path (str): The path string to validate.

    Returns:
        list: [bool, str]
              - bool: True if valid, False otherwise.
              - str: Reason for invalidity or "Valid path".
    """
    # 1. Check for None or Empty
    if not path:
        return [False, "Path is empty"]

    if not isinstance(path, str):
        return [False, "Input must be a string"]

    # 2. Check for Null Character
    if '\0' in path:
        return [False, "Path contains null character"]

    # 3. Check Length (Standard MAX_PATH is 260)
    # Note: Windows 10+ supports long paths, but 260 is the safe standard limit.
    if len(path) > 260:
        return [False, "Path exceeds maximum length (260 characters)"]

    # 4. Check for Invalid Characters (excluding separators and colon for now)
    # Invalid chars: < > " | ? *
    # Separators allowed: \ and /
    invalid_chars_pattern = r'[<>"|?*]'
    match = re.search(invalid_chars_pattern, path)
    if match:
        return [False, f"Path contains invalid character: '{match.group()}'"]

    # 5. Check Colon Usage (Drive Letter)
    # Colon is only allowed at index 1 for drive letters (e.g., C:),
    # unless it's a UNC path or special prefix.
    colon_count = path.count(':')
    if colon_count > 1:
        return [False, "Path contains multiple colons"]
    elif colon_count == 1:
        # Handle special prefix \\?\ which allows long paths
        prefix_offset = 0
        if path.startswith('\\\\?\\'):
            prefix_offset = 4
            # If prefix exists, the colon should be after the prefix + drive letter
            # e.g. \\?\C:\ -> colon is at index 5
            expected_colon_index = prefix_offset + 1
        else:
            expected_colon_index = 1

        if path.index(':') != expected_colon_index:
            return [False, "Colon is not in a valid position for drive letter"]

        # Check if the character before colon is a letter
        if not path[expected_colon_index - 1].isalpha():
            return [False, "Drive letter must be an alphabetic character"]

    # 6. Split Path into Components to check names
    # Treat both \ and / as separators
    parts = re.split(r'[\\/]', path)

    # Filter out empty strings resulting from leading/trailing separators or double separators
    # However, we need to be careful not to filter out legitimate root logic if needed,
    # but for name validation, empty parts between separators are usually okay (normalized by OS)
    # We focus on non-empty parts for name rules.
    non_empty_parts = [p for p in parts if p]

    # Reserved Names (Case-insensitive)
    reserved_names = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    }

    for part in non_empty_parts:
        # Check Reserved Names
        # Note: Reserved names apply if the part matches exactly (ignoring extension logic for simplicity here)
        # Technically CON.txt is valid, CON is invalid.
        # We check the base name without extension for strict reserved check,
        # but for this format check, if the part IS the reserved name, it's invalid.
        part_upper = part.upper()

        # Extract base name for reserved check (e.g., "CON" in "CON" is invalid, "CON.TXT" is valid)
        base_name = part_upper.split('.')[0] if '.' in part else part_upper

        if base_name in reserved_names and part_upper == base_name:
             return [False, f"Path contains reserved name: '{part}'"]

        # Check Trailing Spaces or Dots
        # Exception: '.' and '..' are valid directory references
        if part not in ('.', '..'):
            if part.endswith(' ') or part.endswith('.'):
                return [False, f"Path component '{part}' cannot end with space or dot"]

    return [True, "Valid path"]

def is_valid_folder_file_name(name: str) -> [bool, str]:
    """
    检查给定字符串是否为 Windows 下不合法的文件夹或文件名称。
    返回 False True 表示合法。
    """
    if not isinstance(name, str):
        print(name)
        return [False, "not instance"]

    # 1. 空字符串或全是空白
    if not name or name.isspace():
        print(name)
        return [False, "The string is all blank"]

    # 2. 包含非法字符
    illegal_chars = r'[<>:"|?*]'
    if re.search(illegal_chars, name):
        print(name)
        return [False, "Illegal"]

    # 3. 以空格或点结尾（Windows 不允许）
    if name.endswith(' ') or name.endswith('.'):
        print(name)
        return [False, "End with space or dot"]

    # 4. 是保留设备名（不区分大小写）
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL',
        *(f'COM{i}' for i in range(1, 10)),
        *(f'LPT{i}' for i in range(1, 10))
    }
    if name.upper() in reserved_names:
        print(name)
        return [False, "Containing keep device name."]

    # 5. 长度超过 255（单个文件夹名限制）
    if len(name) > 255:
        print(name)
        return [False, "Too long"]

    return [True, "Valid folder name"]

def check_env_vars(required_vars):
    missing_vars = [var for var in required_vars if var not in os.environ]
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")


# Example Usage:
if __name__ == "__main__":
    test_cases = [
        "C:\\Users\\Test\\file.txt",
        "C:\\Users\\Test\\file<.txt",
        "C:\\CON",
        "C:\\folder\\",
        "C:\\folder\\.",
        "C:\\folder\\ ",
        "file.txt",
        "",
        "C:\\path\\to\\file:name.txt"
        ""
    ]

    for case in test_cases:
        result = is_valid_windows_path_format(case)
        print(f"Path: '{case}' -> Valid: {result[0]}, Reason: {result[1]}")