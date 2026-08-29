import os
from langchain_core.tools import tool

COMPOSE_FILENAMES = [
    "docker-compose.yml",
    "docker-compose.yaml",
    "docker-configure.yaml",
    "docker-configure.yml",
]


@tool
def find_compose_file(repo_path: str) -> str:
    """
    Locate the docker compose file in a repo, checking common naming
    variants including the non-standard 'docker-configure.yaml'.

    Args:
        repo_path: Absolute local path to the cloned repository.

    Returns:
        The filename of the compose file found, or an error if none exists.
    """
    if not os.path.exists(repo_path):
        return f"Error: path '{repo_path}' does not exist."

    top_level_files = set(os.listdir(repo_path))
    for filename in COMPOSE_FILENAMES:
        if filename in top_level_files:
            return f"Found compose file: {filename}"

    return ("Error: no docker compose file found at top level (checked: "
             + ", ".join(COMPOSE_FILENAMES) + ")")