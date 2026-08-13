import os
import sys
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from providers import get_providers
from orchestrator import Orchestrator
import tools

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML_PATH = os.path.join(SERVER_DIR, "static", "index.html")
CONFIG_PATH = os.path.join(SERVER_DIR, "project_dir_config.json")

# Make sure static directory exists
os.makedirs(os.path.join(SERVER_DIR, "static"), exist_ok=True)

def load_project_dir():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                data = json.load(f)
                path = data.get("project_dir")
                if path and os.path.exists(path):
                    return os.path.abspath(path)
        except Exception:
            pass
    # Default to scratch folder or current working directory
    default_dir = os.path.join(os.path.dirname(SERVER_DIR), "scratch", "workspace")
    os.makedirs(default_dir, exist_ok=True)
    return os.path.abspath(default_dir)

def save_project_dir(path):
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump({"project_dir": os.path.abspath(path)}, f)
    except Exception:
        pass

# Initialize project directory state
current_project_dir = load_project_dir()
os.chdir(current_project_dir)

class ProjectDirRequest(BaseModel):
    path: str

@app.get("/")
def read_root():
    if not os.path.exists(INDEX_HTML_PATH):
        return {"error": f"Frontend index.html not found at: {INDEX_HTML_PATH}. Please build it first."}
    return FileResponse(INDEX_HTML_PATH)

@app.get("/api/project_dir")
def get_project_dir():
    return {"project_dir": current_project_dir}

@app.post("/api/set_project_dir")
def set_project_dir(req: ProjectDirRequest):
    global current_project_dir
    target_path = os.path.abspath(req.path)
    try:
        os.makedirs(target_path, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create or access directory: {str(e)}")
    
    current_project_dir = target_path
    save_project_dir(current_project_dir)
    os.chdir(current_project_dir)
    return {"status": "success", "project_dir": current_project_dir}

@app.get("/api/files")
def get_files():
    files_list = []
    ignored_dirs = {".git", "__pycache__", "venv", ".venv", ".pytest_cache", ".agents"}
    
    try:
        for root, dirs, files in os.walk(current_project_dir):
            # Modify dirs in-place to ignore specified subfolders
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, current_project_dir)
                # Use forward slash for path uniformity
                rel_path_slash = rel_path.replace(os.path.sep, "/")
                files_list.append({
                    "name": file,
                    "path": rel_path_slash,
                    "size": os.path.getsize(full_path)
                })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"files": sorted(files_list, key=lambda x: x["path"])}

@app.get("/api/file")
def get_file_content(path: str = Query(...)):
    safe_path = path.replace("/", os.path.sep)
    abs_path = os.path.abspath(os.path.join(current_project_dir, safe_path))
    
    # Path traversal check
    if not abs_path.startswith(current_project_dir):
        raise HTTPException(status_code=400, detail="Path traversal detected")
        
    if not os.path.exists(abs_path) or os.path.isdir(abs_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return {"path": path, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    loop = asyncio.get_running_loop()
    
    try:
        # Wait for task prompt from browser
        data = await websocket.receive_text()
        history = []
        try:
            payload = json.loads(data)
            task_prompt = payload.get("prompt", "").strip()
            history = payload.get("history", [])
        except Exception:
            task_prompt = data.strip()

        if not task_prompt:
            await websocket.send_json({"type": "error", "message": "Task prompt cannot be empty."})
            await websocket.close()
            return

        # Ensure server process is in the latest directory
        os.chdir(current_project_dir)

        # Initialize providers
        providers = get_providers()
        if not providers:
            await websocket.send_json({
                "type": "error", 
                "message": "No active Groq providers initialized. Ensure GROQ_API_KEY is set in .env."
            })
            await websocket.close()
            return

        orchestrator = Orchestrator(
            providers=providers,
            tools=[tools.read_file, tools.write_file, tools.list_dir, tools.run_bash]
        )

        # 1. Send planning event
        await websocket.send_json({"type": "status", "message": "Planning... Decomposing request into subtasks..."})
        subtasks = orchestrator.plan(task_prompt, history=history)
        await websocket.send_json({
            "type": "plan",
            "subtasks": subtasks
        })

        # Pre-flight warnings log
        warnings = orchestrator.get_preflight_warnings(subtasks)
        for warn in warnings:
            await websocket.send_json({"type": "status", "message": warn})

        # 2. Build thread-safe live logger callback
        def on_tool_call(agent_name, tool_name, args, provider_name):
            event = {
                "type": "tool_call",
                "agent_name": agent_name,
                "tool_name": tool_name,
                "args": args,
                "provider_name": provider_name
            }
            asyncio.run_coroutine_threadsafe(websocket.send_json(event), loop)

        # 3. Run workers in parallel
        await websocket.send_json({"type": "status", "message": "Executing workers in parallel..."})
        results, conflicts, execution_warnings = await orchestrator.run_workers(subtasks, on_tool_call=on_tool_call, history=history)

        # 4. Stream worker done events
        for subtask_id, result in results.items():
            subtask_title = next((st["title"] for st in subtasks if st["id"] == subtask_id), "Unknown Subtask")
            await websocket.send_json({
                "type": "worker_done",
                "subtask_id": subtask_id,
                "subtask_title": subtask_title,
                "result": result
            })

        # 5. Stream conflict events if any occurred
        if conflicts:
            for conflict in conflicts:
                await websocket.send_json({
                    "type": "conflict",
                    "path": conflict["path"],
                    "workers": conflict["workers"],
                    "winners": conflict["winners"],
                    "resolved": conflict.get("resolved", False),
                    "error": conflict.get("error")
                })

        # 6. Stream execution warnings if any occurred
        if execution_warnings:
            for warning in execution_warnings:
                await websocket.send_json({
                    "type": "execution_warning",
                    "subtask_id": warning["subtask_id"],
                    "path": warning["path"],
                    "message": warning["message"]
                })

        # 7. Send final summary completion signal
        await websocket.send_json({"type": "summary", "message": "All subtasks completed successfully."})

    except WebSocketDisconnect:
        print("WebSocket client disconnected.")
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
