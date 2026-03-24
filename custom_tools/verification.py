import re
from pathlib import PureWindowsPath  # 注意：用 PureWindowsPath，不依赖当前系统

def is_valid_windows_path_format(path_str):
    """
    检查字符串是否符合 Windows 文件路径的格式规范（不检查是否存在）。
    返回 True 表示格式合理，False 表示明显非法。
    """
    if not isinstance(path_str, str):
        return False

    s = path_str.strip()
    if not s:
        return False

    # --- 1. 检查非法字符 ---
    illegal_chars = '<>"|?*'
    if any(c in s for c in illegal_chars):
        return False

    # --- 2. 不能以空格或 '.' 结尾（Windows 会自动去除，导致歧义）---
    if s.endswith(' ') or s.endswith('.'):
        return False

    # --- 3. 尝试用 PureWindowsPath 解析（不会访问文件系统）---
    try:
        p = PureWindowsPath(s)
    except Exception:
        return False

    # --- 4. 检查各部分（文件名/目录名）是否为保留名 ---
    # Windows 保留设备名（不区分大小写）
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL',
        *(f'COM{i}' for i in range(1, 10)),
        *(f'LPT{i}' for i in range(1, 10))
    }

    # 分解路径的每个部分（去掉盘符和根）
    try:
        parts = p.parts
        # 在 Windows 中，p.parts 可能包含盘符如 'C:'，跳过它
        for part in parts:
            # 去掉末尾的 '.' 或空格（虽然前面已检查结尾，但中间部分也可能有？）
            clean_part = part.rstrip('. ')
            if clean_part.upper() in reserved_names:
                return False
    except ValueError:
        return False

    # --- 5. 长度限制（可选）---
    # Windows 最大路径长度通常为 260（MAX_PATH），但启用长路径后可达 32767
    # 这里不强制限制，除非你有特殊需求

    return True

import re
import os

def is_valid_folder_file_name(name: str) -> bool:
    """
    检查给定字符串是否为 Windows 下不合法的文件夹或文件名称。
    返回 False True 表示合法。
    """
    if not isinstance(name, str):
        return False

    # 1. 空字符串或全是空白
    if not name or name.isspace():
        return False

    # 2. 包含非法字符
    illegal_chars = r'[<>:"|?*]'
    if re.search(illegal_chars, name):
        return False

    # 3. 以空格或点结尾（Windows 不允许）
    if name.endswith(' ') or name.endswith('.'):
        return False

    # 4. 是保留设备名（不区分大小写）
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL',
        *(f'COM{i}' for i in range(1, 10)),
        *(f'LPT{i}' for i in range(1, 10))
    }
    if name.upper() in reserved_names:
        return False

    # 5. 长度超过 255（单个文件夹名限制）
    if len(name) > 255:
        return False

    # 6. 全是点（如 '...'）——虽然技术上可能被允许，但通常视为无效
    if all(c == '.' for c in name):
        return False

    return True

def check_env_vars(required_vars):
    missing_vars = [var for var in required_vars if var not in os.environ]
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

if __name__ == "__main__":
    print("hello")
    print(is_valid_windows_path_format("E:/Projects/Agent/generated_code/bayesian_linear_regression.py"))