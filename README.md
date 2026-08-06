# CodeHive - Multi-Agent Parallel CLI Coding CLI

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
│ Worker Agent 1│    │ Worker Agent 2│    │ Worker Agent 3│ (Executed Concurrently
└───────+───────┘    └───────+───────┘    └───────+───────┘  in ThreadPoolExecutor)
        │                    │                    │
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ▼
    (read_file / write_file / list_dir / run_bash) → feed result back → repeat
    until the model returns plain text with no tool call
    │       │       │
    └───┬───┴───────┘
         ▼
   print a summary panel per subtask in original order
```

## Setup & Usage

1. **Get your API Keys**:
   - **Groq Key** (Required): Get a free key at [Groq Console](https://console.groq.com).
   - **NVIDIA Key** (Optional fallback): Get a free key at [NVIDIA Build](https://build.nvidia.com).
2. **Install requirements**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure API Keys**:
   - **PowerShell**: 
     ```powershell
     $env:GROQ_API_KEY="your_groq_key_here"
     $env:NVIDIA_API_KEY="your_nvidia_key_here" # Optional
     ```
   - **CMD**:
     ```cmd
     set GROQ_API_KEY=your_groq_key_here
     set NVIDIA_API_KEY=your_nvidia_key_here
     ```
   - **Unix/macOS**:
     ```bash
     export GROQ_API_KEY="your_groq_key_here"
     export NVIDIA_API_KEY="your_nvidia_key_here"
     ```
4. **Run the CLI**:
   ```bash
   python main.py
   ```

### Quick Start (Windows)

For a quick setup on Windows:
* Double-click [`start_codehive.bat`](file:///C:/Users/santhosh/.gemini/antigravity/scratch/CodeHive/start_codehive.bat).
* Paste your API keys when prompted (Groq key is required; NVIDIA key is optional).
* Start typing tasks directly in the CLI!

## File Structure

| File | Purpose |
|---|---|
| [`tools.py`](file:///C:/Users/santhosh/.gemini/antigravity/scratch/CodeHive/tools.py) | Tool implementations: `read_file`, `write_file`, `list_dir`, `run_bash`. |
| [`providers.py`](file:///C:/Users/santhosh/.gemini/antigravity/scratch/CodeHive/providers.py) | Multi-provider initialization (`groq` & `nvidia`). |
| [`agent.py`](file:///C:/Users/santhosh/.gemini/antigravity/scratch/CodeHive/agent.py) | `Agent` class wrapping the chat completion tool loop with multi-provider fallback. |
| [`orchestrator.py`](file:///C:/Users/santhosh/.gemini/antigravity/scratch/CodeHive/orchestrator.py) | `Orchestrator` class: Splits task into subtasks and runs workers concurrently. |
| [`main.py`](file:///C:/Users/santhosh/.gemini/antigravity/scratch/CodeHive/main.py) | REPL entrypoint using `rich` for layout, colors, and thread-safe streaming logs. |
| [`requirements.txt`](file:///C:/Users/santhosh/.gemini/antigravity/scratch/CodeHive/requirements.txt) | Project dependencies (`groq`, `openai`, `rich`). |
| [`test_suite.py`](file:///C:/Users/santhosh/.gemini/antigravity/scratch/CodeHive/test_suite.py) | Automated unit and integration testing suite. |

## Already Tested

We have successfully validated the workspace code with a comprehensive test suite in `test_suite.py`. Specifically, the following aspects were verified:
* **Tool Functionality**: `write_file`, `read_file`, `list_dir`, and `run_bash` (with process exit code check) work correctly and catch exceptions.
* **Planner JSON Parsing**: Robust decoding of raw JSON, markdown-fenced JSON responses, and fallback handling when JSON is malformed (creates a single subtask covering the whole request instead of crashing).
* **Parallel Execution / Concurrency**: Timing assertions confirm that 3 worker processes run concurrently using a thread pool executor, taking ~0.2s instead of 0.6s.
* **Agent Manual Loop & Tool Results**: Validated the manual tool execution protocol (using `tool_calls` and `role: "tool"` messages) via simulated multi-turn chats.

To execute the test suite yourself:
```bash
python test_suite.py
```

## Conflict Resolution & File Claims (v3)

CodeHive v3 includes a proactive **File Claim Registry** and a reactive **LLM Reconciler Agent** to automatically handle and resolve concurrent write conflicts.

### 1. File Claim Registry (Proactive)
* **Write Interception**: When a worker starts a `write_file` tool call, it registers a lock claim on the file path with the thread-safe `ClaimRegistry`.
* **Real-time Live Alerts**: If another worker tries to claim the same file path, a contested claim event warning is printed directly to the live streaming CLI. Note: This is purely informative to give early visibility and does not block worker thread execution.

### 2. Reconciler Agent (Reactive Auto-Merge)
* **Divergent State Parsing**: If a conflict is confirmed post-execution, CodeHive pulls the file's original pre-run baseline content, the winners' and losers' written versions, and each worker's instructions.
* **LLM Merge Call**: A Reconciler model is invoked using the active provider pool to combine all edits into a single resolved code string while preserving the intent of all workers.

### 3. Fallback & Safety Net
Before writing the reconciler's merged output to disk, CodeHive runs two sanity checks:
* **Syntax Compilation**: If the target is a `.py` file, it is compiled using `ast.parse()`. If syntax is invalid, the merge is rejected.
* **Selection Check**: If the merged content is byte-identical to any of the input versions (meaning the LLM simply chose one worker's version instead of merging changes), it is rejected.
* **Graceful Fallback**: If checks fail, the last-write-wins file remains intact on disk, and the CLI prints a red conflict panel detailing the merge failure alongside the clobbered code for manual recovery. If checks pass, the combined output is written to disk, and a yellow `CONFLICT AUTO-MERGED` panel is displayed.

This dual-layer mechanism was built using empirical evidence gathered from concurrent race testing to ensure parallel productivity without risking silent data corruption.

## Multi-Provider Fallback (Groq → NVIDIA NIM)

To maximize the free-tier rate limits, CodeHive implements a **Multi-Provider Fallback Routing** logic:
- ** headrooms**: Groq's free tier offers 30 RPM, and NVIDIA NIM offers ~40 RPM. Setting up both key credentials gives CodeHive a combined ceiling of ~70 RPM.
- **Sequential Fallback**: When a worker agent is rate-limited (status 429/503) on Groq, it immediately retries the exact same payload on the NVIDIA NIM provider (using `meta/llama-3.3-70b-instruct`) without pausing or sleeping.
- **Sleep Backoff**: Standard exponential backoff-and-sleep is only triggered if all active providers in the fallback list fail.
- **Best-Effort Routing**: This is a fallback headroom multiplier, not a quality/cost-optimized router. If `NVIDIA_API_KEY` is omitted, CodeHive runs on Groq-only mode automatically without erroring.

## History & Key Migration

CodeHive originally launched using the Google GenAI SDK (`gemini-3.5-flash`). However, real-world development testing regularly hit Gemini's free-tier rate limits (5-10 RPM), stalling workers mid-task. 

To overcome this, CodeHive migrated to the **Groq API** utilizing `llama-3.3-70b-versatile` (offering a much higher 30 RPM limit on its free tier). This migration required rewriting `agent.py` to target OpenAI/Groq-style tool schemas and function call message structures.

## Known Limits

* **Conflict Resolution & Over-Deletion Risk**: Auto-merge is performed using a single model turn. While protected by syntax and selection checks, the reconciler can sometimes silently delete unrelated code (e.g. helper functions or untouched routes) that no worker requested to modify. Users must treat `CONFLICT AUTO-MERGED` as a warning to manually review changes on disk rather than a guarantee of correctness.
* **Rate Limits**: Free-tier rate limits apply; the agents automatically back off and retry up to 3 times on 429/503 errors.

## Natural Next Steps

* **Interactive Merge Editor**: Showing a diff comparison panel in the REPL allowing users to choose merge paths interactively.
* **Streaming Token Output**: Real-time response token streaming in the terminal.
* **Shared Context**: A persistent context registry allowing workers to coordinate.
* **Slash Commands**: Integration of terminal shortcuts like `/plan`, `/agents`, `/clear`.
