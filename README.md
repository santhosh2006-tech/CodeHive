# CodeHive - Multi-Agent Parallel CLI Coding Agent

CodeHive is a multi-agent developer CLI that uses a planner model to decompose complex coding requests into 1 to 4 independent subtasks, executing them concurrently using a thread pool of worker developer agents. Each worker agent runs inside its own loop with direct file and bash execution tools.

```
                  ┌──────────────────────┐
                  │  User Prompt (input) │
                  └──────────┬───────────┘
                             ▼
                  ┌──────────────────────┐
                  │     Planner LLM      │
                  └──────────┬───────────┘
                             │ (JSON subtasks output)
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ Worker Agent 1│    │ Worker Agent 2│    │ Worker Agent 3│ (Executed Concurrently)
└───────+───────┘    └───────+───────┘    └───────+───────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ▼
    (read_file / write_file / list_dir / run_bash) → feed result back → repeat
                             ▼
                   Conflict Detection & Auto-Merge
                             ▼
                   Summary printed to terminal
```

## Key Features

✅ **True Parallel Execution** - Multiple workers execute simultaneously, not sequentially  
✅ **Automatic Conflict Resolution** - LLM-based reconciliation when workers modify the same file  
✅ **Multi-Provider Fallback** - Seamless failover between Groq and NVIDIA NIM APIs  
✅ **Intelligent Error Handling** - Non-transient errors (400, 401, 403, 404, 422) fail fast without retry  
✅ **Execution Monitoring** - Tracks tool calls and warns about claimed-but-not-executed operations  
✅ **File Claim Registry** - Proactive warnings when multiple workers target the same file  
✅ **Comprehensive Testing** - 15+ unit and integration tests with mocked API responses

## Setup & Usage

### 1. Get Your API Keys

- **Groq Key** (Required): Get a free key at [Groq Console](https://console.groq.com)
- **NVIDIA Key** (Optional fallback): Get a free key at [NVIDIA Build](https://build.nvidia.com)

### 2. Install Requirements

```bash
pip install -r requirements.txt
```

### 3. Configure API Keys

**PowerShell:**
```powershell
$env:GROQ_API_KEY="your_groq_key_here"
$env:NVIDIA_API_KEY="your_nvidia_key_here"  # Optional
```

**CMD:**
```cmd
set GROQ_API_KEY=your_groq_key_here
set NVIDIA_API_KEY=your_nvidia_key_here
```

**Unix/macOS:**
```bash
export GROQ_API_KEY="your_groq_key_here"
export NVIDIA_API_KEY="your_nvidia_key_here"
```

Alternatively, copy `.env.example` to `.env` and fill in your keys.

### 4. Run the CLI
```bash
python main.py
```

### 5. Run the Web Interface (FastAPI / WebSockets)
```bash
python -m uvicorn server:app --host 127.0.0.1 --port 8086 --reload
```
Open **http://127.0.0.1:8086** in your browser. This web UI features real-time parallel streaming logs of worker agents via WebSockets.

### Quick Start (Windows)
- Double-click `start_codehive.bat` to launch the CLI.
- Double-click `start_codehive_web.bat` to launch the FastAPI Web server and automatically open the browser.

## Example Usage

```
hive > build a simple flask api with a /health endpoint and a README

[Scale Test] Planning microservices catalog...

=== PLAN BREAKDOWN ===
Subtask 1: Create Flask app structure
Subtask 2: Implement /health endpoint
Subtask 3: Write README documentation
======================

Executing scale task waves...
[Worker-1] Calling tool write_file(path="app.py", content="...")
[Worker-2] Calling tool write_file(path="health.py", content="...")
[Worker-3] Calling tool write_file(path="README.md", content="...")

=== SCALE TEST RESULTS ===
Results Count: 3
Conflicts Count: 0
Execution Warnings: []
```

## File Structure

| File | Purpose |
|------|---------|
| `tools.py` | Tool implementations: `read_file`, `write_file`, `list_dir`, `run_bash` |
| `providers.py` | Multi-provider initialization (Groq & NVIDIA NIM) |
| `agent.py` | `Agent` class wrapping the chat completion tool loop with multi-provider fallback |
| `orchestrator.py` | `Orchestrator` class: Splits task into subtasks and runs workers concurrently |
| `main.py` | REPL entrypoint using `rich` for layout, colors, and thread-safe streaming logs |
| `requirements.txt` | Project dependencies (`groq`, `openai`, `rich`) |
| `test_suite.py` | Automated unit and integration testing suite |

## Conflict Resolution (v4)

CodeHive uses a native Git worktree-based conflict resolution architecture:

### 1. Git Worktree Isolation
- Each worker executes inside a dedicated Git worktree (`codehive-worker-<subtask_id>`) checked out to a separate task branch (`task/<subtask_id>`).
- Direct filesystem changes from different workers are isolated during execution.

### 2. Native Git Merge & LLM Reconciler
- When a wave of concurrent workers finishes, CodeHive commits each branch and merges it sequentially into the active branch.
- **Merge Conflicts**: If sequential merging results in a Git merge conflict, CodeHive parses the conflict, isolates the conflicted file, and triggers the LLM-based reconciler.
- **Safety Checks**:
  - Python syntax validation (`ast.parse`) is performed on the reconciled content.
  - Byte-identical merges are rejected (no-op detection).
- **Fallback**: If reconciliation fails, CodeHive uses last-write-wins and flags the conflict for manual review.

### 3. Winner/Loser Classification
- Analyzes worker writes against the resolved merge content to dynamically log the winning worker (whose changes matched the merge output) and the losers.

### 4. Execution Warnings & Audit
- Monitors tool usage. Warns if a worker claimed they completed a subtask but no execution tools (like `run_bash`) or code writes were observed.
- Blocks execution if workers bypass compile-time syntax checks.

## Multi-Provider Fallback (Groq → NVIDIA NIM)

To maximize free-tier rate limits:

- **Groq**: 30 RPM free tier with `llama-3.3-70b-versatile`
- **NVIDIA NIM**: ~40 RPM free tier with `meta/llama-3.3-70b-instruct`
- **Combined capacity**: ~70 RPM
- **Sequential Fallback**: On 429/503 errors, immediately retries on alternate provider
- **Sleep Backoff**: Only triggered if all providers fail
- **Graceful Degradation**: Works with Groq-only if NVIDIA key not provided

## Already Tested

Comprehensive test suite validates:

✅ Tool functionality (write/read/list/bash with exit code checks)  
✅ Planner JSON parsing (raw JSON, markdown-fenced, malformed fallback)  
✅ True parallel execution (timing assertions confirm concurrency)  
✅ Agent tool-calling loop (simulated multi-turn chats with tool results)  
✅ Rate limit retry with exponential backoff  
✅ Collision detection and winner/loser identification  
✅ Conflict resolution (3-worker race with auto-merge)  
✅ Non-conflicting scenarios (independent file writes)  
✅ Reconciler markdown extraction and syntax validation  
✅ Identical input rejection (merge no-op detection)  
✅ Provider fallback (Groq → NVIDIA on 429 errors)  
✅ Both-providers-fail retry backoff propagation

To run tests:
```bash
python test_suite.py
```

## Known Limitations

⚠️ **Auto-merge over-deletion risk**: Reconciler can occasionally remove unrelated code (helpers, untouched functions). Always review `CONFLICT AUTO-MERGED` warnings.

⚠️ **Rate limits**: Free-tier limits apply. Agents automatically back off and retry up to 3 times on 429/503 errors.

⚠️ **Non-transient errors**: 400/401/403/404/422 errors fail fast without retry - by design, not a bug.

## Architecture Highlights

### Error Handling
- **Non-transient errors** (400, 401, 403, 404, 422) fail immediately without retry
- **Transient errors** (429, 503) trigger multi-provider fallback then exponential backoff
- Worker failures are caught and logged without crashing the orchestrator
- Each worker's failure is isolated - other workers continue unaffected

### Concurrency
- Uses `ThreadPoolExecutor` for true parallel execution
- Thread-safe file claim registry with RLock
- Thread-safe logging with print_lock
- Results returned in original subtask order despite parallel completion

### Tool System
- Four core tools: `read_file`, `write_file`, `list_dir`, `run_bash`
- All tools return error strings instead of raising exceptions
- `run_bash` includes 60-second timeout
- `write_file` auto-creates parent directories

## Natural Next Steps

- **Interactive Merge Editor**: Diff comparison panel for manual conflict resolution
- **Streaming Token Output**: Real-time response token streaming in terminal
- **Persistent Shared Context**: Workers can see siblings' progress mid-run
- **Slash Commands**: `/plan`, `/agents`, `/clear` for CLI shortcuts
- **Wave-based Dependencies**: Explicit depends_on graph execution

## License

MIT License

## Contributing

Pull requests welcome! Please ensure tests pass before submitting:
```bash
python test_suite.py
```

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

**Built with ❤️ using Groq, NVIDIA NIM, and Rich Terminal UI**
