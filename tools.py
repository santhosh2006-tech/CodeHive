import os
import subprocess

def read_file(path: str) -> str:
    """Reads the contents of a file at the specified path.
    
    Args:
        path: The path to the file to read.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"ERROR: {str(e)}"

def write_file(path: str, content: str) -> str:
    """Writes the specified content to a file at the given path.
    Creates parent directories if they do not exist.
    
    Args:
        path: The path to the file to write.
        content: The text content to write.
    """
    try:
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Success: File written to {path}"
    except Exception as e:
        return f"ERROR: {str(e)}"

def list_dir(path: str = ".") -> str:
    """Lists the contents of the directory at the specified path.
    
    Args:
        path: The directory path to list (defaults to current directory '.').
    """
    try:
        items = os.listdir(path)
        result = []
        for item in items:
            item_path = os.path.join(path, item)
            is_dir = os.path.isdir(item_path)
            prefix = "[DIR] " if is_dir else "[FILE]"
            result.append(f"{prefix} {item}")
        return "\n".join(result) if result else "(Empty directory)"
    except Exception as e:
        return f"ERROR: {str(e)}"

def run_bash(command: str) -> str:
    """Runs a shell command on the host environment and returns the output.
    Times out after 60 seconds.
    
    Args:
        command: The shell command to execute.
    """
    try:
        res = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        return f"EXIT CODE: {res.returncode}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    except subprocess.TimeoutExpired as e:
        return f"ERROR: Command timed out after 60 seconds.\nSTDOUT:\n{e.stdout or ''}\nSTDERR:\n{e.stderr or ''}"
    except Exception as e:
        return f"ERROR: {str(e)}"
