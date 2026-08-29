from git import Repo
from git.exc import GitCommandError
from langchain_core.tools import tool
import os
import re


def _extract_repo_name(repo_url: str) -> str:
    """Derive a clean folder name from a git URL, e.g. .../Secure_FTP.git -> Secure_FTP"""
    name = repo_url.rstrip("/").split("/")[-1]
    name = re.sub(r"\.git$", "", name)
    return name


@tool
def clone_repo(repo_url: str, destination_path: str) -> str:
    """
    Clone a git repository into a NEW subfolder (named after the repo) inside
    the given destination path. Does not clone directly into destination_path itself.

    Args:
        repo_url: The HTTPS URL of the repository to clone (e.g. https://github.com/user/repo.git)
        destination_path: Absolute local path under which a new repo-named folder will be created.

    Returns:
        A status message including the final path the repo was cloned into.
    """
    try:
        repo_name = _extract_repo_name(repo_url)
        final_path = os.path.join(destination_path, repo_name)

        if os.path.exists(final_path) and os.listdir(final_path):
            return f"Error: '{final_path}' already exists and is not empty."

        os.makedirs(final_path, exist_ok=True)
        Repo.clone_from(repo_url, final_path)
        return f"Successfully cloned {repo_url} into {final_path}"
    except GitCommandError as e:
        return f"Git error while cloning: {str(e)}"
    except Exception as e:
        return f"Unexpected error while cloning: {str(e)}"