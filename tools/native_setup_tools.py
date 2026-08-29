# create_venv, install_deps
import subprocess
import os
from langchain_core.tools import tool
import sys

@tool
def get_venv_python_path(repo_path: str) -> str:
    """
    Get the absolute path to the Python/pip executables inside a repo's
    .venv, accounting for OS differences (Windows vs Unix).

    Args:
        repo_path: Absolute local path to the repo containing a .venv folder.

    Returns:
        The absolute paths to venv's python and pip executables.
    """
    venv_path = os.path.join(repo_path, ".venv")
    if not os.path.exists(venv_path):
        return f"Error: no .venv found at {venv_path}. Run create_venv first."

    if sys.platform == "win32":
        python_path = os.path.join(venv_path, "Scripts", "python.exe")
        pip_path = os.path.join(venv_path, "Scripts", "pip.exe")
    else:
        python_path = os.path.join(venv_path, "bin", "python")
        pip_path = os.path.join(venv_path, "bin", "pip")

    return f"python: {python_path}\npip: {pip_path}"

@tool
def create_venv(repo_path: str) -> str:
    """
    Create a standard Python virtual environment (.venv) inside the given
    repo path using the built-in venv module.

    Args:
        repo_path: Absolute local path to the cloned repository.

    Returns:
        A status message indicating success or failure.
    """
    if not os.path.exists(repo_path):
        return f"Error: path '{repo_path}' does not exist."

    venv_path = os.path.join(repo_path, ".venv")
    if os.path.exists(venv_path):
        return f".venv already exists at {venv_path}, skipping creation."

    try:
        result = subprocess.run(
            ["python", "-m", "venv", ".venv"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return f"Error creating venv: {result.stderr}"
        return f"Successfully created virtual environment at {venv_path}"
    except subprocess.TimeoutExpired:
        return "Error: venv creation timed out after 60s."
    except Exception as e:
        return f"Unexpected error creating venv: {str(e)}"