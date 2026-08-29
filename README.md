# Repo Setup Agent

An AI agent that automates local development environment setup for open-source
repositories. Give it a GitHub repo URL and a destination folder, and it clones
the repo, analyzes its structure, detects the tech stack, checks prerequisites,
and sets up the environment — with human confirmation required before any
install command actually runs.

Built with [DeepAgents](https://github.com/langchain-ai/deepagents) (on
LangGraph) + Groq for LLM inference.

## Status: Work in Progress

This is an active capstone project. Phases 0–3 are complete and tested.
Phase 4 (verification) and some polish items are still in progress.

### ✅ Completed

- **Phase 0 — Environment setup**: `uv`-managed Python project, DeepAgents +
  Groq wired up and confirmed working.
- **Phase 1 — Repo analysis**: clones any public GitHub repo into a
  repo-named subfolder, scans its structure, and reports findings grounded
  strictly in real file/folder data (no hallucinated guesses).
- **Phase 2 — Stack detection & native setup**:
  - Detects Python (pip/poetry/pipenv), Node (npm/yarn/pnpm/bun), Go, Rust,
    Ruby, Java from manifest files.
  - Checks whether required tools (python, node, npm, etc.) are actually
    installed on the system before recommending install steps.
  - For Python projects: creates an isolated `.venv` and installs
    dependencies into it (not system-wide).
  - For Node/Go/Rust/etc.: installs directly via the appropriate package
    manager (no extra environment needed).
  - **Human-in-the-loop confirmation gate**: the agent always pauses and
    asks for explicit approval before running any install command. This is
    enforced at the framework level (LangGraph interrupts), not just a
    prompt instruction.
- **Phase 3 — Docker support**: detects `docker-compose.yml` /
  `docker-configure.yaml` variants, brings up services with
  `docker compose up -d` (confirmation-gated), and verifies containers
  are running via `docker compose ps`.

### 🚧 In progress

- **Phase 4 — Verification**: currently the agent trusts a `0` exit code as
  "success." Next step is a real smoke test per stack (e.g. `pip check` for
  Python, confirming `node_modules/` is populated for Node) so failures that
  don't show up in the exit code still get caught.
- **Multi-package-manager handling**: when a repo has signals for more than
  one package manager (e.g. both `package-lock.json` and `bun.lockb`), the
  agent currently picks one on its own. Planned fix: have it ask the user
  which to use instead.
- **Prerequisite auto-install**: currently the agent only *reports* missing
  tools (e.g. "Node.js not found, install it from nodejs.org") rather than
  installing them — this is a deliberate safety choice, not a bug.

### Not started yet

- Final CLI polish (currently uses raw `input()` prompts)
- Cleanup of scratch/debug test scripts

## Setup

Requires [uv](https://docs.astral.sh/uv/) and a [Groq API key](https://console.groq.com).

```bash
git clone https://github.com/anshul-honey-kashif-minor/Github-setup-agent.git
cd Github-setup-agent
uv sync
```

Create a `.env` file in the project root:

GROQ_API_KEY=your_key_here


## How to run

```bash
uv run main.py
```

You'll be prompted for:
1. **Repo URL** — the GitHub repo you want to set up (e.g.
   `https://github.com/someuser/somerepo`)
2. **Destination path** — a local folder where it should be cloned (e.g.
   `D:\dev\workspace`) — the agent creates a repo-named subfolder inside it.

The agent will then:
1. Clone the repo
2. Analyze its structure and detect the tech stack
3. Check that required tools are installed
4. Report its findings and **ask you to confirm** before installing anything
5. Once you type `yes`, it will attempt setup (venv + pip, npm/yarn/bun
   install, or `docker compose up`, depending on the stack) — pausing
   **again** for explicit approval right before the actual install command
   executes
6. Report the result

Type `yes`/`no` at each prompt as requested.

**Note:** if the repo uses Docker, make sure Docker Desktop is running
before starting the agent.

## Tech stack

- [DeepAgents](https://github.com/langchain-ai/deepagents) on LangGraph —
  agent orchestration, planning, and human-in-the-loop interrupts
- [Groq](https://groq.com) (`openai/gpt-oss-20b`) — LLM inference
- `uv` — Python environment/dependency management
- `GitPython` — repo cloning
