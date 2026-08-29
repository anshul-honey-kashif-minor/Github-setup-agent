from tools.shell_tools import run_shell

pip_path = r"D:\MAJOR1\proj\workspace\network_analyzer\.venv\Scripts\pip.exe"
result = run_shell.invoke({
    "cmd": f"{pip_path} install -r requirements.txt",
    "cwd": r"D:\MAJOR1\proj\workspace\network_analyzer",
    "timeout": 900 
})
print(result)