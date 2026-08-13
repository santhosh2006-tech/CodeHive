import os
import sys
import asyncio
import threading
from dotenv import load_dotenv

# Load environment variables from .env file at the very top
load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from providers import get_providers
from orchestrator import Orchestrator
import tools

# Console for rich logging and UI
console = Console()
print_lock = threading.Lock()

# Fail loudly and clearly if GROQ_API_KEY is missing
if not os.environ.get("GROQ_API_KEY"):
    console.print(Panel(
        "[bold red]CRITICAL ERROR: GROQ_API_KEY is not set in your environment or .env file![/bold red]\n\n"
        "Please copy [bold].env.example[/bold] to [bold].env[/bold] and fill in your Groq key:\n"
        "  [yellow]GROQ_API_KEY=your_key_here[/yellow]\n\n"
        "Get a free API key at [link=https://console.groq.com]Groq Console[/link].",
        title="[bold red]Configuration Required[/bold red]",
        border_style="red"
    ))
    sys.exit(1)

def on_tool_call(agent_name: str, tool_name: str, args: dict, provider_name: str = "unknown"):
    """Callback for live tool-call logging from parallel worker threads."""
    color_map = {
        "Worker-1": "cyan",
        "Worker-2": "green",
        "Worker-3": "magenta",
        "Worker-4": "yellow",
    }
    color = color_map.get(agent_name, "white")
    
    # Format args as arg_name="value"
    args_str = ", ".join(f'{k}={repr(v)}' for k, v in args.items())
    
    with print_lock:
        console.print(
            f"[{color}][{agent_name}][/{color}] (via {provider_name}) Calling tool "
            f"[bold yellow]{tool_name}[/bold yellow]({args_str})"
        )

async def process_task(providers: list, user_prompt: str):
    """Coordinates task planning and parallel execution."""
    orchestrator = Orchestrator(
        providers=providers,
        tools=[tools.read_file, tools.write_file, tools.list_dir, tools.run_bash]
    )

    console.print("\n[bold blue]Planning... Decomposing request into subtasks...[/bold blue]")
    subtasks = orchestrator.plan(user_prompt)

    # Print the planning breakdown panel
    subtasks_text = ""
    for subtask in subtasks:
        subtasks_text += f"[bold cyan]Subtask {subtask['id']}:[/bold cyan] {subtask['title']}\n"
        subtasks_text += f"  Instructions: {subtask['instructions']}\n\n"

    console.print(Panel(
        subtasks_text.strip(),
        title="[bold yellow]Plan Breakdown[/bold yellow]",
        border_style="yellow"
    ))

    console.print("[bold blue]Executing workers in parallel...[/bold blue]\n")

    # Run all workers concurrently
    results, conflicts, execution_warnings = await orchestrator.run_workers(subtasks, on_tool_call=on_tool_call)

    console.print("\n[bold green]All subtasks finished! Summarizing results:[/bold green]\n")

    # Print execution warnings if any
    if execution_warnings:
        warn_text = ""
        for warn in execution_warnings:
            warn_text += f"[bold yellow]Worker-{warn['subtask_id']}:[/bold yellow] {warn['message']}\n"
        console.print(Panel(
            warn_text.strip(),
            title="[bold yellow]Execution Warnings[/bold yellow]",
            border_style="yellow"
        ))

    # Print final summaries in original subtask order
    for subtask in subtasks:
        subtask_id = subtask["id"]
        title = subtask["title"]
        result = results.get(subtask_id, "No result returned.")

        console.print(Panel(
            result,
            title=f"[bold green]Result for Subtask {subtask_id}: {title}[/bold green]",
            border_style="green"
        ))

    # Print conflict alert panel if any collisions occurred
    if conflicts:
        for conflict in conflicts:
            path = conflict["path"]
            all_workers = ", ".join(f"Worker-{w}" for w in conflict["workers"])
            winners = ", ".join(f"Worker-{w}" for w in conflict["winners"])
            
            if conflict.get("resolved"):
                merged_text = (
                    f"[bold yellow]CONFLICT AUTO-MERGED[/bold yellow]\n\n"
                    f"[bold]{path}[/bold] was modified concurrently by: {all_workers}\n\n"
                    f"[bold red]IMPORTANT:[/bold red] Auto-merge is best-effort. It may compile cleanly but still contain [bold red]over-deletions[/bold red] (e.g. removing helper functions or untouched routes).\n"
                    f"[bold yellow]Please review the merged file contents on disk directly to confirm correctness against subtask intents.[/bold yellow]"
                )
                console.print(Panel(
                    merged_text,
                    title="[bold yellow]Conflict Auto-Merged[/bold yellow]",
                    border_style="yellow"
                ))
            else:
                err_suffix = f" ({conflict.get('error')})" if conflict.get("error") else ""
                conflict_text = (
                    f"[bold]{path}[/bold] was modified concurrently by: {all_workers}\n"
                    f"Final content matches: {winners if winners else 'None'}\n"
                    f"Automatic merge was attempted and failed{err_suffix} — manual review needed.\n"
                )
                for worker_id, w in conflict["losers"]:
                    conflict_text += f"\n[bold red]Likely LOST: Worker-{worker_id}'s changes to {path}[/bold red]\n"
                    conflict_text += "--- Intended Content ---\n"
                    conflict_text += f"{w['content']}\n"
                    conflict_text += "------------------------\n"
                    
                console.print(Panel(
                    conflict_text.strip(),
                    title="[bold red]CONFLICT DETECTED[/bold red]",
                    border_style="red"
                ))

async def main():
    # Initialize available providers
    providers = get_providers()

    # Visual banner
    console.print(Panel(
        Text("Welcome to CodeHive\nMulti-Agent Parallel CLI Coding Agent", justify="center", style="bold yellow"),
        border_style="yellow",
        expand=False
    ))

    # REPL loop
    while True:
        try:
            user_input = Prompt.ask("\n[bold green]hive[/bold green] [yellow]>[/yellow]")
            if user_input.strip().lower() in ("exit", "quit"):
                console.print("[bold yellow]Exiting CodeHive. Goodbye![/bold yellow]")
                break
            if not user_input.strip():
                continue

            await process_task(providers, user_input)

        except KeyboardInterrupt:
            console.print("\n[bold yellow]Task interrupted. Returning to prompt.[/bold yellow]")
        except Exception as e:
            console.print(f"[bold red]Error: {str(e)}[/bold red]")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Goodbye![/bold yellow]")
        sys.exit(0)
