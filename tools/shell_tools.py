import subprocess
import shlex
import shutil
import os
from langchain_core.tools import tool

ALLOWED_EXECUTABLES = {
    "pip", "python", "python3",
    "npm", "yarn", "pnpm", "bun",
    "docker",
    "git",
    "bundle", "go", "cargo", "mvn", "gradle",
}

BLOCKED_PATTERNS = ["rm -rf", "sudo", "curl ", "wget ", "&&", "||", ";", "|", ">", "<"]


@tool
def run_shell(cmd: str, cwd: str, timeout: int = 600) -> str:
    """
    Run a whitelisted shell command inside a specific directory. Only
    approved package-manager/build executables are allowed. Destructive
    patterns are blocked. Requires human confirmation before execution
    (enforced by the agent's interrupt configuration).

    Args:
        cmd: The full command to run, e.g. "pip install -r requirements.txt"
        cwd: Absolute path to run the command in.
        timeout: Max seconds to allow the command to run (default 600).

    Returns:
        Command output (stdout/stderr) or an error message.
    """
    for pattern in BLOCKED_PATTERNS:
        if pattern in cmd:
            return f"Error: command blocked — contains disallowed pattern '{pattern}'."

    try:
        parts = shlex.split(cmd, posix=False)
    except ValueError as e:
        return f"Error: could not parse command — {str(e)}"

    if not parts:
        return "Error: empty command."

    executable = parts[0]
    executable_basename = os.path.basename(executable).replace(".exe", "").replace(".cmd", "")
    if executable_basename not in ALLOWED_EXECUTABLES:
        return f"Error: '{executable}' is not in the allowed executables list."

    # Resolve the real path (handles .cmd/.bat on Windows, and full paths like venv pip)
    if os.path.isabs(executable) and os.path.exists(executable):
        resolved_executable = executable
    else:
        resolved_executable = shutil.which(executable)
        if resolved_executable is None:
            return f"Error: executable '{executable}' not found on system PATH."

    parts[0] = resolved_executable

    try:
        result = subprocess.run(
            parts,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        output = f"Exit code: {result.returncode}\n"
        if result.stdout:
            output += f"STDOUT:\n{result.stdout[-2000:]}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr[-2000:]}\n"
        return output
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout}s."
    except FileNotFoundError:
        return f"Error: executable '{executable}' not found on system PATH."
    except Exception as e:
        return f"Unexpected error running command: {str(e)}"