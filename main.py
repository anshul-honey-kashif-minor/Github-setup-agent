import os
from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from deepagents import create_deep_agent
from langchain_groq import ChatGroq
from tools.git_tools import clone_repo
from tools.fs_tools import scan_repo_tree
from tools.prereq_tools import check_prerequisites
from tools.detect_tools import detect_stack
from tools.native_setup_tools import create_venv,get_venv_python_path
from tools.shell_tools import run_shell
from tools.docker_tools import find_compose_file

load_dotenv()

model = ChatGroq(
    model="openai/gpt-oss-20b",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
  #  max_retries=0,
)
system_prompt = """You are a repo setup assistant. Given a GitHub repo URL and a
local destination path, your job is to:

1. Clone the repository using clone_repo. Note: clone_repo creates a NEW
   subfolder named after the repo inside destination_path, and its return
   message tells you the exact final path the repo was cloned into. Use
   THAT exact path for all subsequent steps, not the original destination_path.
2. If clone_repo returns an error, STOP immediately and report the exact
   error message to the user. Do not proceed or make up information.
3. Scan the repo's structure (using the final cloned path) with scan_repo_tree.
4. Run detect_stack on the same path to determine the tech stack and
   recommended install command.
5. Run check_prerequisites using the detected stack name(s) (e.g.
   "python-pip", "node-npm", "node-bun") to verify the required tools are
   installed on this system BEFORE recommending installation. If multiple
   stacks were detected, check prerequisites for each one.
6. Report your findings so far, grounded only in the exact output of these tools:
   - The project's primary language/stack and package manager (from detect_stack)
   - The recommended install command (from detect_stack)
   - Prerequisite check results (from check_prerequisites) — clearly state
     whether required tools are installed, and if anything is missing,
     include the exact install guidance the tool provided
   - The exact list of key config/setup files found (from scan_repo_tree)
   - Whether Docker files were present or not
   - The top-level folder structure
7. If any required prerequisite is missing for the chosen stack, DO NOT
   proceed to installation. Clearly tell the user what's missing and how
   to install it, then stop and wait for the user's next message.
8. If prerequisites are satisfied, STOP and wait for explicit user
   confirmation before running any install command. Do not proceed to
   step 9 without it.
9. Once confirmed, branch based on the detected stack:
   - If PYTHON (pip/poetry/pipenv): call create_venv first, then
     get_venv_python_path to get the exact pip executable path inside the
     .venv. Run the install command via run_shell using that FULL pip path
     (not just "pip"), so packages install into the isolated .venv instead
     of the system Python. Example: run_shell with
     cmd="<venv_pip_path> install -r requirements.txt"
   - If NODE (npm/yarn/pnpm/bun), GO, RUST, RUBY, or JAVA: these package
     managers scope dependencies to the project directory automatically.
     Do NOT call create_venv. Just run the recommended install command
     directly via run_shell with cwd set to the repo path.
     Example: run_shell with cmd="npm install", cwd="<repo_path>"
   - If DOCKER files were detected: call find_compose_file to get the exact
     compose filename (it may be docker-compose.yml, docker-compose.yaml,
     or docker-configure.yaml). Run
     "docker compose -f <compose_filename> up -d" via run_shell using that
     exact filename. After it completes, run
     "docker compose -f <compose_filename> ps" via run_shell to verify
     containers are running, and include that status in your report.
   - If no stack was detected: report this clearly and do not attempt
     any install.
10. Report the install result (success/failure, exact output) grounded
    only in run_shell's actual return value.

Never say phrases like "likely," "appears to be," or "without more information."
Do not speculate beyond what the tools returned.

Be concise. Do not narrate your reasoning process, do not re-explain the plan
before or after each tool call. Keep reports under 150 words.
"""
checkpointer = InMemorySaver()

agent = create_deep_agent(
    tools=[clone_repo, scan_repo_tree, detect_stack, create_venv, get_venv_python_path, run_shell, check_prerequisites,find_compose_file],
    system_prompt=system_prompt,
    model=model,
    interrupt_on={
        "run_shell": True,   # always pause for human approval before running
    },
    checkpointer=checkpointer,
)

def print_step(step):
    for node_name, node_output in step.items():
        # Skip internal middleware noise entirely
        if node_name in ("__interrupt__", "PatchToolCallsMiddleware.before_agent",
                          "HumanInTheLoopMiddleware.after_model"):
            continue

        if not isinstance(node_output, dict) or "messages" not in node_output:
            continue

        for msg in node_output["messages"]:
            content = getattr(msg, "content", "")
            tool_calls = getattr(msg, "tool_calls", None)

            if tool_calls:
                for tc in tool_calls:
                    args_str = ", ".join(f"{k}={v}" for k, v in tc["args"].items())
                    print(f"🔧 Running: {tc['name']}({args_str})")

            elif content:
                # Tool results come back with node_name == "tools"
                if node_name == "tools":
                    preview = content[:200] + ("..." if len(content) > 200 else "")
                    print(f"   ✓ {preview}\n")
                else:
                    print(f"\n💬 Agent:\n{content}\n")

if __name__ == "__main__":
    repo_url = input("Enter repo URL: ").strip()
    dest_path = input("Enter destination path: ").strip()

    config = {"configurable": {"thread_id": "repo-setup-session-1"}}

    print("Starting agent run...\n")

    for step in agent.stream({
        "messages": [{
            "role": "user",
            "content": f"Clone {repo_url} to {dest_path}, then analyze it and set up the environment."
        }]
    }, config=config, stream_mode="updates"):
        print_step(step)

    proceed = input("\nProceed with installation? (yes/no): ").strip().lower()
    if proceed == "yes":
        for step in agent.stream({
            "messages": [{
                "role": "user",
                "content": "Yes, proceed with the installation now."
            }]
        }, config=config, stream_mode="updates"):
            print_step(step)
    else:
        print("Skipping installation.")

    state = agent.get_state(config)   # <-- MOVED HERE, now checked fresh after the install attempt
    while state.next:
        if state.tasks and state.tasks[0].interrupts:
            interrupt_info = state.tasks[0].interrupts[0]
            print("=" * 50)
            print("CONFIRMATION NEEDED")
            print(interrupt_info.value)
            print("=" * 50)
            approve = input("Run this command? (yes/no): ").strip().lower()

            if approve == "yes":
                for step in agent.stream(
               Command(resume={"decisions": [{"type": "approve"}]}),
               config=config,
               stream_mode="updates"
               ):
                    print_step(step)
            else:
                for step in agent.stream(
                  Command(resume={"decisions": [{"type": "reject", "message": "User rejected the command."}]}),
                  config=config,
                  stream_mode="updates"
               ):
                    print_step(step)
                    print("Command rejected. Stopping here.")
                    break
            state = agent.get_state(config)
        else:
            break

    print("\n=== Run complete ===")