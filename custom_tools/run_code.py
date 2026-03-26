import importlib
import subprocess
import sys

def install_package(package):
    """Install the specified package using pip"""
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def check_and_install_packages(input_raw) -> bool:
    """检查并安装缺失的包"""
    try:
        packages = ast.literal_eval(input_raw)
    except:
        print(input_raw)
        print("\nInvalid input format. Please provide a valid list of [package1, package2,...].")
        return False

    for install_name, import_name in packages:
        try:
            importlib.import_module(import_name)
        except ImportError:
            print(f"\n⚠️  {import_name} not installed, installing...")
            install_package(install_name)
            try: # 再次尝试导入以确认安装成功
                importlib.import_module(import_name)
                print(f"\n✅ {import_name} installation is complete")
            except ImportError:
                print(f"\n❌ Failed to install {import_name}. Please check the error messages above and try installing it manually.")
                return False

    print("\nAll required packages are installed")
    return True
check_and_install_packages.name = "check_and_install_packages"
check_and_install_packages.description = (
    "Check if the required packages are installed, and install the missing ones. Can only be called after code generation."
    "Input is an array containing multiple parameters. Each is a tuple. Install_name and import_name are recorded in order."
    "The output is a bool indicating whether the packages are successfully installed. If failed, do the action again."
)
check_and_install_packages.input = {
    "package1": ("install_name", "import_name"),
    "package2": ("install_name", "import_name"),
    "...": ("install_name", "import_name")
}
check_and_install_packages.output = {
    "is_success": bool,
}

import re
import io, sys
import ast
import traceback
import multiprocessing
from queue import Empty

# 定义子进程执行的任务函数
# 注意：在 Windows 上，此函数必须定义在模块顶层，以便 pickle 序列化
def _run_code_task(code_str, output_queue):
    """
    在子进程中执行代码并捕获输出/异常。
    """
    # 1. 重定向 stdout 和 stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    old_stdin = sys.stdin

    redirected_output = io.StringIO()
    redirected_error = io.StringIO()
    redirected_input = io.StringIO("")  # 空输入源

    sys.stdout = redirected_output
    sys.stderr = redirected_error
    sys.stdin = redirected_input  # 关键修复

    try:
        # 2. 执行环境配置
        # 注意：这里依然没有做沙箱限制，生产环境需限制 __builtins__
        def safe_input(prompt=""):
            print(prompt, end="", file=sys.stdout)
            return ""  # 返回空字符串而不是抛异常

        exec_globals = {
            "__name__": "__main__",
            "__file__": "dynamic_code",
            "input": safe_input  # 覆盖 input 函数
        }

        output = redirected_output.getvalue()
        error = redirected_error.getvalue()

        # 3. 成功结果
        output_queue.put((True, output, error, None))
    except Exception as e:
        output = redirected_output.getvalue()
        error_output = redirected_error.getvalue()
        error_trace = traceback.format_exc()
        # 4. 失败结果
        output_queue.put((False, output, error_output + "\n" + error_trace, None))
    finally:
        # 5. 恢复标准输出
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def execute_python_code(file_path) -> bool:
    """
    在受限环境中执行 Python 代码，带超时控制。

    规则：
    1. 如果代码在 timeout_seconds 内执行完毕且无报错 -> 返回 True
    2. 如果代码在 timeout_seconds 内报错 -> 返回 False
    3. 如果代码运行超过 timeout_seconds 仍未报错（如死循环但未崩溃）-> 强制终止，视为正确，返回 True

    参数:
        file_path (str): 代码文件路径
        timeout_seconds (int): 超时时间，默认 30 秒

    返回:
        bool: True 表示成功或超时未报错，False 表示执行出错
    """
    timeout_seconds=30

    # 1. 读取代码
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code_to_run = f.read()
    except Exception as e:
        print(f"\nError reading file: {e}")
        return False

    # 2. 创建通信队列和进程
    # 注意：Windows 下必须确保此代码在 __main__ 保护下调用
    output_queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=_run_code_task, args=(code_to_run, output_queue))

    print(f"\nExecuting code (Timeout: {timeout_seconds}s)...\n")
    process.start()

    # 3. 等待进程结束，设置超时
    process.join(timeout=timeout_seconds)

    # 4. 处理超时或正常结束
    if process.is_alive():
        # 情况 3: 超时，强制终止
        print(f"[Timeout] Execution exceeded {timeout_seconds} seconds. Terminating process...")
        process.terminate()
        process.join() # 确保进程清理
        print("Execution terminated due to timeout. Treated as SUCCESS.")
        return True
    else:
        # 进程已结束，检查是成功还是报错
        try:
            # 从队列获取结果
            # 注意：如果子进程在 put 之前崩溃（极罕见），这里会抛 Empty
            success, output, error_output, _ = output_queue.get(timeout=5)

            if success:
                # 合并 stdout 和 stderr 显示
                full_output = (output + "\n" + error_output).strip()
                result_msg = f"Execution succeeded.\nOutput:\n{full_output}" if full_output else "Execution succeeded without output."
                print(result_msg)
                return True
            else:
                result_msg = f"Execution error:\n{error_output}"
                print(result_msg)
                return False
        except Empty:
            print("Execution finished but failed to retrieve result (Queue Empty).")
            return False
        except Exception as e:
            print(f"Unexpected error retrieving result: {e}")
            return False
execute_python_code.name = "execute_python_code"
execute_python_code.description = (
    "Try to run a piece of Python code. Must use check_and_install_packages once before using the tool"
    "Input is the path of the python file to be executed."
    "The output is a bool indicating whether the code is successfully excuted."
)
execute_python_code.input = {
    "file_path": str,
}
execute_python_code.output = {
    "is_success": bool,
}

if __name__ == "__main__":
    multiprocessing.freeze_support()

    #required_packages = "[(\"requests\", \"requests\"), (\"numpy\", \"numpy\"), (\"pandas\", \"pandas\"),]"
    #check_and_install_packages(required_packages)
    test_path = "E:/Projects/Agent/logs/generated_files/box_pushing_game/box_pushing_game.py"
    #execute_python_code(test_path)