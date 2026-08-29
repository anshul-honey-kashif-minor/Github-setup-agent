import shutil
from langchain_core.tools import tool

# Maps a detected stack name to the executable(s) it actually needs on PATH
STACK_REQUIREMENTS = {
    "python-pip": ["python", "pip"],
    "python-poetry": ["python", "poetry"],
    "python-pipenv": ["python", "pipenv"],
    "node-npm": ["node", "npm"],
    "node-yarn": ["node", "yarn"],
    "node-pnpm": ["node", "pnpm"],
    "node-bun": ["bun"],
    "ruby": ["ruby", "bundle"],
    "go": ["go"],
    "rust": ["cargo"],
    "java-maven": ["java", "mvn"],
    "java-gradle": ["java", "gradle"],
    "docker": ["docker"],
}


@tool
def check_prerequisites(stack_name: str) -> str:
    """
    Check whether the executables required for a given detected stack are
    installed and available on the system PATH.

    Args:
        stack_name: The stack identifier as returned by detect_stack,
            e.g. "python-pip", "node-npm", "node-bun", "docker".

    Returns:
        A report of which required executables are present or missing,
        with install guidance for anything missing.
    """
    required = STACK_REQUIREMENTS.get(stack_name)
    if required is None:
        return f"Unknown stack '{stack_name}' — no prerequisite check available for it."

    missing = []
    found = []
    for exe in required:
        path = shutil.which(exe)
        if path:
            found.append(f"{exe} -> {path}")
        else:
            missing.append(exe)

    install_guidance = {
        "python": "Install Python from https://python.org/downloads (adds pip automatically)",
        "pip": "Comes bundled with Python — reinstall Python if missing",
        "poetry": "Install via https://python-poetry.org/docs/#installation",
        "pipenv": "Install via: pip install pipenv",
        "node": "Install Node.js (includes npm) from https://nodejs.org",
        "npm": "Comes bundled with Node.js — reinstall Node if missing",
        "yarn": "Install via: npm install -g yarn",
        "pnpm": "Install via: npm install -g pnpm",
        "bun": "Install from https://bun.sh",
        "ruby": "Install from https://www.ruby-lang.org/en/downloads",
        "bundle": "Install via: gem install bundler",
        "go": "Install from https://go.dev/dl",
        "cargo": "Install Rust (includes cargo) from https://rustup.rs",
        "java": "Install a JDK, e.g. from https://adoptium.net",
        "mvn": "Install Maven from https://maven.apache.org/download.cgi",
        "gradle": "Install from https://gradle.org/install",
        "docker": "Install Docker Desktop from https://www.docker.com/products/docker-desktop",
    }

    if not missing:
        return f"All prerequisites for '{stack_name}' are installed:\n" + "\n".join(found)

    lines = [f"Missing prerequisites for '{stack_name}':"]
    for exe in missing:
        guidance = install_guidance.get(exe, "No installation guidance available.")
        lines.append(f"  - {exe}: NOT FOUND. {guidance}")
    if found:
        lines.append("\nAlready installed:")
        lines.extend(f"  - {f}" for f in found)

    return "\n".join(lines)