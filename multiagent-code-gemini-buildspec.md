# Build Spec: MultiAgent Code (Gemini-powered)

Paste this whole doc as the prompt to Codex / Antigravity / Claude Code.

---

## What to build

A terminal CLI coding agent, similar in spirit to Claude Code, but instead of one
agent working turn-by-turn, a **planner** splits the user's request into independent
subtasks and **multiple worker agents run in parallel**, each with real file and
shell access in the same project directory.

Uses Google AI Studio's Gemini API (free tier) — no paid keys.

## Architecture

```
user types a task in the terminal
        │
        ▼
   [planner agent] → splits into 1-4 independent subtasks, returns JSON
        │
   ┌────┼────┬────────┐
   ▼    ▼    ▼         
[worker-1][worker-2][worker-3]   ← run CONCURRENTLY (asyncio.gather or ThreadPoolExecutor)
   │       │       │
   each worker loops: call Gemini → if it requests a tool call, run the tool
   (read_file / write_file / list_dir / run_bash) → feed result back → repeat
   until the model returns plain text with no tool call
   │       │       │
   └───┬───┴───────┘
       ▼
  print a summary panel per subtask
```

## Files to create

| File | Purpose |
|---|---|
| `tools.py` | Tool implementations: `read_file`, `write_file`, `list_dir`, `run_bash`, plus their function-declaration schemas for Gemini |
| `agent.py` | `Agent` class: wraps a Gemini chat session with a system prompt/role, runs a tool-calling loop until the model finishes, with a `max_turns` safety cap |
| `orchestrator.py` | `Orchestrator` class: calls a planner prompt to split the task into subtasks (JSON), then runs worker `Agent`s in parallel, returns results keyed by subtask id in original order |
| `main.py` | Terminal REPL entrypoint using `rich` for panels/colors: banner, prompt loop, live logging of tool calls, final summary panel. `exit`/`quit` to leave, Ctrl+C handled gracefully |
| `requirements.txt` | `google-genai`, `rich` |
| `README.md` | Setup + usage instructions (see "README content" below) |

## Gemini API specifics (use the `google-genai` SDK, not the deprecated `google-generativeai`)

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
```

- Free API key from **https://aistudio.google.com/apikey** (no credit card).
- Default model: `gemini-2.5-flash` (fast, generous free tier, good tool-calling). Make
  the model name a constructor arg so it's easy to swap (e.g. to `gemini-2.5-pro` for
  higher quality on harder tasks).
- Define tools as Gemini function declarations (`types.FunctionDeclaration` /
  `types.Tool`), not OpenAI-style — the schema shape is different from Groq/OpenAI, so
  don't copy an OpenAI tools array verbatim.
- Tool-calling loop shape: send messages → check `response.candidates[0].content.parts`
  for `function_call` parts → execute the matching local function → send back a
  `function_response` part → repeat until a turn has only text parts, no function calls.
- Handle the case where Gemini returns multiple function calls in a single turn
  (execute all, return all results before the next turn).

## Behavioral requirements (carry over from the Groq prototype — keep these)

1. **Planner prompt** must return ONLY raw JSON (no markdown fences) of shape:
   `{"subtasks": [{"id": "1", "title": "...", "instructions": "..."}]}`. Strip markdown
   fences defensively before `json.loads`, and if parsing fails, fall back to a single
   subtask covering the whole original request — never crash on a bad planner response.
2. **Worker prompt**: careful senior engineer, has file/shell tools, must write real
   working code (not pseudocode), and must finish with a plain-text summary (no tool
   call) once done.
3. **True parallelism**: workers must run concurrently, not take turns. Prove it works
   with a quick local test using fake/mocked responses (no real API calls) that times
   N simulated workers and confirms wall-clock time is close to a single worker's time,
   not N times it.
4. **Tool safety basics**: `run_bash` should have a timeout (60s is fine) and return
   stdout/stderr/exit code as a single string; `write_file` should create parent dirs
   if missing; every tool function should catch exceptions and return an `"ERROR: ..."`
   string rather than raising, so a bad tool call doesn't kill the whole agent loop.
5. **Max turns cap** per agent (e.g. 15) so a confused agent can't loop forever.
6. **Result ordering**: even though workers finish at different times, the final
   summary must be printed in the original subtask order.
7. **CLI feel**: banner on startup, a visually distinct panel for the planner's
   breakdown, live streamed lines for each agent's tool calls as they happen (not just
   at the end), a colored summary panel per subtask at the end. Exit cleanly on
   `exit`/`quit`/Ctrl+C.

## Testing expectations before calling it done

Don't just claim it works — actually verify, the same way you'd verify any prototype:
- Unit-test each tool function directly (write then read a file, list a dir, run a
  trivial shell command) and confirm the returned content is correct.
- Test the agent's tool-calling loop with a **mocked** Gemini response (simulate one
  function-call turn followed by one text-only turn) and confirm it actually invokes
  the right tool and returns the final text — no real API key/spend needed for this.
- Test the planner's JSON parsing against both a clean response and a
  markdown-fenced response, confirming both parse correctly, and confirm the
  malformed-JSON fallback produces a single sane subtask instead of crashing.
- Time a parallel run with mocked workers (e.g. 3 workers, each sleeping 0.2s) and
  assert total wall-clock time is close to 0.2s, not 0.6s, to prove genuine
  concurrency rather than sequential execution.
- Clean up any test artifacts/files created during testing before finishing.

## README content to include

- What it does and the architecture diagram above.
- Setup: get a free key at https://aistudio.google.com/apikey, `pip install -r
  requirements.txt`, `export GEMINI_API_KEY="..."`, `python main.py`.
- File table (same as "Files to create" above).
- "Already tested" section listing what was actually verified (from the testing
  section above) — be specific, not just "it works."
- Known limits: no cross-agent conflict detection yet if two agents touch the same
  file (planner tries to keep subtasks independent but doesn't guarantee it);
  Gemini free-tier rate limits still apply if you run many tasks back to back.
- "Natural next steps": conflict detection/negotiation between agents when they touch
  the same file, streaming token output, a persistent `shared_context.json` so
  siblings can see each other's progress mid-run, slash commands (`/plan`, `/agents`,
  `/clear`).

## Explicitly out of scope for this first pass

- No VS Code extension, no web UI — terminal only.
- No conflict negotiation between agents yet — that's a deliberate v2 feature, not a
  bug to fix now.
- No persistence/database — a single run, printed to terminal, is enough.
