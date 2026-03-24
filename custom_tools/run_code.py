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

def execute_python_code(file_path) -> bool:
    """
    在受限环境中执行 Python 代码，返回 stdout 或异常信息。
    注意：此实现仅用于演示，生产环境需加强安全限制！
    """
    with open(file_path, "r", encoding="utf-8") as f:
        code_to_run = f.read()

    # 重定向输出
    print("\nExecuting code:\n")
    old_stdout = sys.stdout
    redirected_output = io.StringIO()
    sys.stdout = redirected_output

    try:
        # 执行代码
        exec_globals = {"__name__": "__main__"}
        exec(code_to_run, exec_globals)
        output = redirected_output.getvalue()
        result = f"\nExecution succeeded.\nOutput:\n{output}" if output else "Execution succeeded without output."
        print(result)
    except Exception as e:
        result = f"\nExecution error:\n{traceback.format_exc()}"
        print(result)
        return False
    finally:
        sys.stdout = old_stdout

    print(result)
    return True
execute_python_code.name = "execute_python_code"
execute_python_code.description = (
    "Try to run a piece of Python code. Must use check_and_install_packages once before using the tool"
    "Input is the path of the python file to be executed."
    "The output is a bool indicating whether the code is successfully excuted. If failed, check and fix code"
)
execute_python_code.input = {
    "file_path": str,
}
execute_python_code.output = {
    "is_success": bool,
}

if __name__ == "__main__":
    required_packages = "[(\"requests\", \"requests\"), (\"numpy\", \"numpy\"), (\"pandas\", \"pandas\"),]"
    check_and_install_packages(required_packages)
    test_path = "E:/Projects/Python/agent_test/randomforest/randomforest.py"
    execute_python_code(test_path)