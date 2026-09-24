import streamlit as st
import tkinter as tk
from uuid import uuid4
from tkinter import filedialog
from agent_core import build_agent
from langgraph.types import Command
st.set_page_config(page_title="SetupPilot", layout="wide")

# --- Custom CSS to constrain width + polish look ---
st.markdown("""
    <style>
        .block-container {
            max-width: 800px;
            padding-top: 3rem;
            margin: 0 auto;
        }
        div[data-testid="stTextInput"] input {
            padding: 0.6rem;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🛠️ SetupPilot")
st.caption("Automated local dev environment setup from a GitHub repo URL")
#st.divider()

# --- Session state init ---
if "dest_path" not in st.session_state:
    st.session_state.dest_path = ""

# --- Folder picker function ---
def pick_folder():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    folder = filedialog.askdirectory()
    root.destroy()
    if folder:
        st.session_state.dest_path = folder

# --- Input form ---
st.subheader("1. Enter Details")

repo_url = st.text_input(
    "GitHub Repo URL",
    placeholder="https://github.com/user/repo.git"
)

dest_col, browse_col = st.columns([5, 1], vertical_alignment="bottom")
with dest_col:
    dest_path = st.text_input(
        "Destination Folder",
        value=st.session_state.dest_path,
        placeholder="e.g. D:\\dev\\workspace"
    )
with browse_col:
    if st.button("📁 Browse", use_container_width=True,key="btn_browse"):
        pick_folder()
        st.rerun()

st.write("")  # small spacing
def start_new_run():
    """Reset Streamlit and LangGraph state while keeping the user's form inputs."""
    agent, checkpointer = build_agent()
    st.session_state.agent = agent
    st.session_state.checkpointer = checkpointer
    st.session_state.thread_id = f"streamlit-session-{uuid4().hex}"
    st.session_state.agent_state = "idle"  # idle | analyzing | awaiting_confirm | running
    st.session_state.pending_interrupt = None
    st.session_state.log = []


if "agent_state" not in st.session_state:
    start_new_run()

config = {"configurable": {"thread_id": st.session_state.thread_id}}

def render_step(step):
    """Render ONE step immediately — live, during the current run."""
    for node_name, node_output in step.items():
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
                    st.markdown(f"🔧 **Running:** `{tc['name']}({args_str})`")
            elif content:
                if node_name == "tools":
                    with st.expander("✓ Tool output", expanded=False):
                        st.code(content, language=None)
                else:
                    st.markdown("**💬 Agent:**")
                    st.markdown(content)


def log_step(step):
    """Parse one streamed step and APPEND it to the persistent log."""
    for node_name, node_output in step.items():
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
                    st.session_state.log.append(("tool_call", f"{tc['name']}({args_str})"))
            elif content:
                if node_name == "tools":
                    st.session_state.log.append(("tool_output", content))
                else:
                    st.session_state.log.append(("agent_msg", content))


def render_log():
    """Render the ENTIRE persisted log — called on every script run (after a rerun)."""
    for kind, content in st.session_state.log:
        if kind == "tool_call":
            st.markdown(f"🔧 **Running:** `{content}`")
        elif kind == "tool_output":
            with st.expander("✓ Tool output", expanded=False):
                st.code(content, language=None)
        elif kind == "agent_msg":
            st.markdown("**💬 Agent:**")
            st.markdown(content)


def run_and_log(user_message):
    """Stream the agent's response: render live AND persist to log."""
    for step in st.session_state.agent.stream(
        {"messages": [{"role": "user", "content": user_message}]},
        config=config,
        stream_mode="updates"
    ):
        render_step(step)   # live display during this run
        log_step(step)      # persist for future reruns


def check_for_interrupt(done_state="idle"):
    """After a stream ends, check if the graph is paused on run_shell.
    If not paused, transition to `done_state` instead of always 'idle'."""
    state = st.session_state.agent.get_state(config)
    if state.next and state.tasks and state.tasks[0].interrupts:
        interrupt_info = state.tasks[0].interrupts[0]
        st.session_state.pending_interrupt = interrupt_info.value
        st.session_state.agent_state = "awaiting_shell_approval"
    else:
        st.session_state.agent_state = done_state


def get_last_exit_code():
    """Scan the log for the most recent 'Exit code: N' from a tool_output entry."""
    import re
    for kind, content in reversed(st.session_state.log):
        if kind == "tool_output":
            match = re.search(r"Exit code:\s*(\d+)", content)
            if match:
                return int(match.group(1))
    return None


st.write("")
run_clicked = st.button(
    "🚀 Run Agent",
    type="primary",
    use_container_width=True,
    disabled=(st.session_state.agent_state != "idle"),
    key="btn_run_agent"
)

if st.button(
    "Start New Run",
    use_container_width=True,
    disabled=(st.session_state.agent_state == "idle" and not st.session_state.log),
    key="btn_start_new_run",
):
    start_new_run()
    st.rerun()

if run_clicked:
    if not repo_url or not dest_path:
        st.error("Please provide both a repo URL and a destination folder.")
    else:
        st.session_state.log = []  # fresh run, clear old log
        st.subheader("2. Progress")
        with st.spinner("Running analysis..."):
            run_and_log(
                f"Clone {repo_url} to {dest_path}, then analyze it and set up the environment."
            )
        check_for_interrupt()
        st.session_state.agent_state = "awaiting_install_confirm"
        st.rerun()

# --- Always render the persisted log so far (after any rerun) ---
if st.session_state.log and not run_clicked:
    st.subheader("2. Progress")
    render_log()

if st.session_state.agent_state == "complete":
    exit_code = get_last_exit_code()
    st.divider()
    if exit_code == 0:
        st.success("✅ **Setup complete!** The environment was configured successfully.")
    elif exit_code is not None:
        st.error(f"❌ **Installation failed** (exit code {exit_code}). Check the tool output above for details.")
    else:
        st.info("ℹ️ Run finished. Review the log above for details.")

elif st.session_state.agent_state == "rejected":
    st.divider()
    st.warning("⏹️ **Command rejected.** No changes were made to the environment.")

# --- Stage: waiting for "proceed with installation?" confirmation ---
if st.session_state.agent_state == "awaiting_install_confirm":
    st.info("⏸️ Agent is waiting: proceed with installation?")
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("✅ Yes, proceed", use_container_width=True, key="btn_install_yes"):
            st.subheader("3. Installing")
            with st.spinner("Working..."):
                run_and_log("Yes, proceed with the installation now.")
            check_for_interrupt()
            st.rerun()
    with col_no:
        if st.button("❌ No, skip", use_container_width=True, key="btn_install_no"):
            st.warning("Installation skipped.")
            st.session_state.agent_state = "idle"

# --- Stage: waiting for run_shell command approval ---
if st.session_state.agent_state == "awaiting_shell_approval":
    interrupt = st.session_state.pending_interrupt
    action = interrupt["action_requests"][0]
    st.warning("⏸️ **Confirmation needed before running a command**")
    st.code(action["args"].get("cmd", ""), language="bash")
    st.caption(f"Working directory: {action['args'].get('cwd', '')}")

    col_approve, col_reject = st.columns(2)
    with col_approve:
        if st.button("✅ Approve & Run", use_container_width=True, type="primary", key="btn_shell_approve"):
            with st.spinner("Running..."):
                for step in st.session_state.agent.stream(
                    Command(resume={"decisions": [{"type": "approve"}]}),
                    config=config,
                    stream_mode="updates"
                ):
                    render_step(step)
                    log_step(step)
            check_for_interrupt(done_state="complete")
            st.rerun()
    with col_reject:
        if st.button("❌ Reject", use_container_width=True, key="btn_shell_reject"):
            with st.spinner("Cancelling..."):
                for step in st.session_state.agent.stream(
                    Command(resume={"decisions": [{"type": "reject", "message": "User rejected the command."}]}),
                    config=config,
                    stream_mode="updates"
                ):
                    render_step(step)
                    log_step(step)
            st.session_state.agent_state = "rejected"
            st.rerun()

if st.session_state.agent_state == "idle" and not run_clicked and not st.session_state.log:
    st.caption("Ready when you are.")
