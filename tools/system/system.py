import logging
import os
import re
import shlex
import subprocess
import platform
from typing import Optional, List
from langchain_core.tools import tool

from tools.utils import _resolve_path, handle_command_errors

logger = logging.getLogger(__name__)

# ============================================================
# Default Whitelist (expanded — dev + launch + file commands)
# ============================================================
DEFAULT_WHITELIST = [
    # System info & navigation (read-only)
    "ipconfig", "dir", "cd", "echo", "notepad", "calc", "mspaint",
    "tasklist", "systeminfo", "hostname", "ver", "set",
    "ping", "tracert", "nslookup", "get-date", "get-process",
    "tree", "whoami", "where", "path", "type", "netstat", "ps",
    "find", "findstr", "sort", "more", "cls", "clear",

    # Development tools
    "code", "python", "python3", "py", "node", "npm", "npx",
    "pip", "pip3", "git", "activate", "call", "venv",
    "pytest", "flake8", "black", "ruff",

    # Launch programs / open paths
    "start", "explorer", "cmd", "powershell", "pwsh",
    "open", "xdg-open",   # Linux/Mac equivalents

    # File/folder management (non-destructive)
    "mkdir", "md", "copy", "xcopy", "robocopy",
    "move", "ren", "rename", "touch", "cat", "head", "tail",
    "wc", "ls", "pwd", "stat", "file",
]

# Characters/sequences that would let a "whitelisted" first command chain
# into an arbitrary, non-whitelisted second command when the raw string
# is handed to a shell. Blocking these closes the whitelist-bypass hole.
# Set ALLOW_CHAINING=1 in .env to disable this check (NOT recommended).
_SHELL_METACHARACTERS = re.compile(r"[;&|`]|\$\(|<\(|>\(|\n|\r")


def _get_custom_whitelist() -> List[str]:
    """Read additional allowed commands from environment variable."""
    custom = os.getenv("ALLOWED_COMMANDS", "")
    if custom:
        return [cmd.strip().lower() for cmd in custom.split(",") if cmd.strip()]
    return []


def _is_whitelist_disabled() -> bool:
    """
    If ALLOW_ALL_COMMANDS=1 (or true/yes) is set in .env, the whitelist
    check is skipped entirely — every command is allowed.
    Use with caution!
    """
    val = os.getenv("ALLOW_ALL_COMMANDS", "").strip().lower()
    return val in ("1", "true", "yes", "on")


def _is_chaining_allowed() -> bool:
    """If ALLOW_CHAINING=1 in .env, shell metacharacters are permitted."""
    val = os.getenv("ALLOW_CHAINING", "").strip().lower()
    return val in ("1", "true", "yes", "on")


def _get_whitelist() -> List[str]:
    """Combine default and custom whitelists."""
    return DEFAULT_WHITELIST + _get_custom_whitelist()


# ============================================================
# Main Tool
# ============================================================
@tool
@handle_command_errors
def execute_system_command(
    command: str,
    timeout: int = 30,
    working_dir: Optional[str] = None
) -> dict:
    """
    Execute a single shell command using the appropriate shell
    (PowerShell on Windows, bash on Unix).

    Parameters:
    - command: A single command (e.g., "dir", "python --version", "pip list").
      Command chaining/piping is NOT allowed by default.
    - timeout: Maximum execution time in seconds (default: 30, max: 300).
    - working_dir: Optional directory where command should run.

    Returns:
    A dictionary with status, output (stdout), error (stderr) if any.
    """
    # Validate timeout
    if not isinstance(timeout, int) or timeout < 1:
        timeout = 30
    timeout = min(timeout, 300)

    # ---- Shell metacharacter check (can be disabled via .env) ----
    if not _is_chaining_allowed() and _SHELL_METACHARACTERS.search(command):
        return {
            "status": "error",
            "error": "Command chaining/piping is not allowed (found one of ; & | ` $( ).",
            "error_type": "not_allowed"
        }

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

    base_command = parts[0].lower()

    # ---- Whitelist check (can be disabled via .env) ----
    if not _is_whitelist_disabled():
        whitelist = _get_whitelist()
        if base_command not in whitelist:
            return {
                "status": "error",
                "error": (
                    f"Command '{base_command}' is not allowed. "
                    f"Allowed commands: {', '.join(whitelist)}. "
                    f"To allow all commands, set ALLOW_ALL_COMMANDS=1 in .env."
                ),
                "error_type": "not_allowed"
            }

    system = platform.system().lower()
    if system == "windows":
        shell_cmd = ["powershell", "-NoProfile", "-Command", command]
    else:
        shell_cmd = ["/bin/bash", "-c", command]

    cwd = None
    if working_dir:
        cwd = str(_resolve_path(working_dir))
        if not os.path.isdir(cwd):
            return {
                "status": "error",
                "error": f"Working directory does not exist: {cwd}",
                "error_type": "invalid_cwd"
            }

    logger.info(f"Executing command: {command}")
    result = subprocess.run(
        shell_cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd
    )

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

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