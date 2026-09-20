from agent_core import build_agent
from langgraph.types import Command

agent, checkpointer = build_agent()

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