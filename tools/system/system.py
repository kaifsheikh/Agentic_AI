import json
import logging
import os
import shlex
import subprocess
import platform
import functools
from typing import Optional, List
from langchain_core.tools import tool

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ============================================================
# Default Whitelist (Safe Commands)
# ============================================================
DEFAULT_WHITELIST = [
    # System info & navigation
    "ipconfig", "dir", "cd", "echo", "start", "notepad", "calc",
    "mspaint", "explorer", "tasklist", "systeminfo", "hostname",
    "ping", "tracert", "nslookup", "get-date", "get-process",
    "tree", "whoami", "where", "path",
    # Development tools
    "code", "python", "node", "npm", "pip", "git", "activate", "call",
    # File operations
    "copy", "move", "rename", "del", "rmdir", "mkdir", "type",
    # Network
    "curl", "wget", "netstat", "ssh", "scp",
    # Process management (read-only)
    "ps", "kill", "taskkill",
]

def _get_custom_whitelist() -> List[str]:
    """Read additional allowed commands from environment variable."""
    custom = os.getenv("ALLOWED_COMMANDS", "")
    if custom:
        return [cmd.strip().lower() for cmd in custom.split(",") if cmd.strip()]
    return []

def _get_whitelist() -> List[str]:
    """Combine default and custom whitelists."""
    return DEFAULT_WHITELIST + _get_custom_whitelist()

# ============================================================
# Helper Decorator for Error Handling
# ============================================================
def _handle_errors(func):
    """Standard error handling for system command tool."""
    @functools.wraps(func)  # Preserves original signature so @tool builds a correct schema
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return json.dumps(result, default=str)
        except subprocess.TimeoutExpired as e:
            logger.warning(f"Command timed out: {e.cmd}")
            return json.dumps({
                "status": "error",
                "error": f"Command timed out after {e.timeout} seconds.",
                "error_type": "timeout"
            })
        except FileNotFoundError as e:
            logger.error(f"Shell not found: {e}")
            return json.dumps({
                "status": "error",
                "error": f"Shell executable not found: {e}",
                "error_type": "shell_not_found"
            })
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            return json.dumps({
                "status": "error",
                "error": str(e),
                "error_type": "unknown"
            })
    return wrapper

# ============================================================
# Main Tool
# ============================================================
@tool
@_handle_errors
def execute_system_command(
    command: str,
    timeout: int = 30,
    working_dir: Optional[str] = None
) -> dict:
    """
    Execute a system command using the appropriate shell (PowerShell on Windows, bash on Unix).
    Only whitelisted commands are allowed for safety.

    Parameters:
    - command: The full command string to execute (e.g., "dir", "python --version", "pip list").
    - timeout: Maximum execution time in seconds (default: 30, max: 300).
    - working_dir: Optional directory where command should run. If relative, resolved against home.

    Returns:
    A dictionary with status, output (stdout), error (stderr) if any.

    Note:
    - The first word of the command (case-insensitive) must be in the whitelist.
    - You can add extra allowed commands via ALLOWED_COMMANDS env variable (comma-separated).
    - Command output is truncated to 10000 characters to avoid memory issues.
    """
    # Validate timeout
    if not isinstance(timeout, int) or timeout < 1:
        timeout = 30
    timeout = min(timeout, 300)  # Cap at 5 minutes

    # Parse command to get first token
    try:
        parts = shlex.split(command)
    except ValueError as e:
        return {
            "status": "error",
            "error": f"Invalid command syntax: {e}",
            "error_type": "invalid_syntax"
        }
    
    if not parts:
        return {
            "status": "error",
            "error": "Empty command.",
            "error_type": "empty_command"
        }

    # Check whitelist
    base_command = parts[0].lower()
    # On Windows, some commands are PowerShell cmdlets like get-date, get-process
    # We treat them as base command names.
    # For commands with paths like ./script.py, we disallow because not in whitelist.
    whitelist = _get_whitelist()
    if base_command not in whitelist:
        return {
            "status": "error",
            "error": f"Command '{base_command}' is not allowed. Allowed commands: {', '.join(whitelist)}",
            "error_type": "not_allowed"
        }

    # Determine shell and command invocation
    system = platform.system().lower()
    if system == "windows":
        shell_cmd = ["powershell", "-NoProfile", "-Command", command]
    else:
        shell_cmd = ["/bin/bash", "-c", command]

    # Prepare working directory
    cwd = None
    if working_dir:
        from tools.utils import _resolve_path  # reuse path resolver
        cwd = str(_resolve_path(working_dir))
        if not os.path.isdir(cwd):
            return {
                "status": "error",
                "error": f"Working directory does not exist: {cwd}",
                "error_type": "invalid_cwd"
            }

    # Execute command
    logger.info(f"Executing command: {command}")
    result = subprocess.run(
        shell_cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd
    )

    # Prepare response
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    # Truncate long outputs
    max_output = 10000
    if len(stdout) > max_output:
        stdout = stdout[:max_output] + f"\n...[TRUNCATED {len(result.stdout) - max_output} chars]"
    if len(stderr) > max_output:
        stderr = stderr[:max_output] + f"\n...[TRUNCATED {len(result.stderr) - max_output} chars]"

    response = {
        "status": "success" if result.returncode == 0 else "error",
        "returncode": result.returncode,
        "output": stdout if stdout else "",
        "error": stderr if stderr else "",
    }

    if result.returncode != 0:
        response["error_type"] = "command_failed"

    return response
