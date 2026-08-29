# detect_stack

import os
from langchain_core.tools import tool

# Order matters: more specific/definitive signals first
STACK_SIGNATURES = [
    ("docker", ["docker-compose.yml", "docker-compose.yaml", "docker-configure.yaml"]),
    ("python-poetry", ["pyproject.toml", "poetry.lock"]),
    ("python-pip", ["requirements.txt"]),
    ("python-pipenv", ["Pipfile"]),
    ("node-npm", ["package-lock.json", "package.json"]),
    ("node-yarn", ["yarn.lock"]),
    ("node-pnpm", ["pnpm-lock.yaml"]),
    ("node-bun", ["bun.lockb"]),
    ("ruby", ["Gemfile"]),
    ("go", ["go.mod"]),
    ("rust", ["Cargo.toml"]),
    ("java-maven", ["pom.xml"]),
    ("java-gradle", ["build.gradle"]),
]


@tool
def detect_stack(repo_path: str) -> str:
    """
    Detect the project's tech stack and package manager by checking for
    known manifest/lock files at the repo's top level.

    Args:
        repo_path: Absolute local path to the cloned repository.

    Returns:
        A structured summary: detected stack(s), confidence, and the
        recommended install command.
    """
    if not os.path.exists(repo_path):
        return f"Error: path '{repo_path}' does not exist."

    top_level_files = set(os.listdir(repo_path))
    detected = []

    for stack_name, signature_files in STACK_SIGNATURES:
        matched = [f for f in signature_files if f in top_level_files]
        if matched:
            detected.append((stack_name, matched))

    if not detected:
        return "No recognized stack detected from top-level manifest files. Manual inspection needed."

    install_commands = {
        "docker": "docker compose up -d",
        "python-poetry": "poetry install",
        "python-pip": "pip install -r requirements.txt",
        "python-pipenv": "pipenv install",
        "node-npm": "npm install",
        "node-yarn": "yarn install",
        "node-pnpm": "pnpm install",
        "node-bun": "bun install",
        "ruby": "bundle install",
        "go": "go mod download",
        "rust": "cargo build",
        "java-maven": "mvn install",
        "java-gradle": "gradle build",
    }

    lines = ["Detected stack(s):"]
    for stack_name, matched_files in detected:
        cmd = install_commands.get(stack_name, "unknown")
        lines.append(f"  - {stack_name} (matched: {', '.join(matched_files)}) -> recommended: `{cmd}`")

    if detected[0][0] == "docker":
        lines.append("\nRecommendation: Docker setup detected — prefer this over native setup.")

    return "\n".join(lines)