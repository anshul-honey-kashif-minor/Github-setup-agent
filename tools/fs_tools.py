# scan_repo_tree, read_file, generate_env_file

import os
from langchain_core.tools import tool

# Files that strongly signal setup/build method — always surface these if present
KEY_FILES = [
    "README.md", "README.rst", "CONTRIBUTING.md",
    "docker-compose.yml", "docker-compose.yaml", "docker-configure.yaml",
    "Dockerfile",
    "requirements.txt", "pyproject.toml", "Pipfile", "setup.py",
    "package.json", "yarn.lock", "pnpm-lock.yaml",
    "Gemfile", "go.mod", "Cargo.toml", "pom.xml", "build.gradle",
    ".env.example", ".env.sample",
    "Makefile",
]

IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}


@tool
def scan_repo_tree(repo_path: str, max_depth: int = 2) -> str:
    """
    Scan a repository's directory structure and flag key setup/config files.

    Args:
        repo_path: Absolute local path to the cloned repository.
        max_depth: How many directory levels deep to scan (default 2).

    Returns:
        A structured text summary: top-level tree + which key config files were found.
    """
    if not os.path.exists(repo_path):
        return f"Error: path '{repo_path}' does not exist."

    found_key_files = []
    tree_lines = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        depth = root[len(repo_path):].count(os.sep)
        if depth > max_depth:
            dirs[:] = []
            continue

        rel_root = os.path.relpath(root, repo_path)
        indent = "  " * depth
        label = os.path.basename(root) if rel_root != "." else os.path.basename(repo_path)
        tree_lines.append(f"{indent}{label}/")

        for f in files:
            tree_lines.append(f"{indent}  {f}")
            if f in KEY_FILES:
                found_key_files.append(os.path.join(rel_root, f) if rel_root != "." else f)

    tree_str = "\n".join(tree_lines[:200])  # cap to avoid context bloat
    key_files_str = "\n".join(found_key_files) if found_key_files else "None found"

    return (
        f"=== Directory structure (depth {max_depth}) ===\n{tree_str}\n\n"
        f"=== Key setup/config files detected ===\n{key_files_str}"
    )