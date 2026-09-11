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
# Default Whitelist (Safe / read-only / dev commands only)
#
# FIX: destructive commands (del, rmdir, kill, taskkill), network
# commands that can exfiltrate data (curl, wget, ssh, scp) and
# "start" (can launch arbitrary programs/URLs) were removed.
# File deletion/movement should go through the dedicated,
# sandboxed file_ops tools instead of a raw shell.
# ============================================================
DEFAULT_WHITELIST = [
    # System info & navigation (read-only)
    "ipconfig", "dir", "cd", "echo", "notepad", "calc", "mspaint",
    "tasklist", "systeminfo", "hostname",
    "ping", "tracert", "nslookup", "get-date", "get-process",
    "tree", "whoami", "where", "path", "type", "netstat", "ps",
    # Development tools
    "code", "python", "node", "npm", "pip", "git", "activate", "call",
]

# Characters/sequences that would let a "whitelisted" first command chain
# into an arbitrary, non-whitelisted second command when the raw string
# is handed to a shell (PowerShell/bash). Blocking these closes the
# whitelist-bypass hole.
_SHELL_METACHARACTERS = re.compile(r"[;&|`]|\$\(|<\(|>\(|\n|\r")


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
    Execute a single whitelisted command using the appropriate shell
    (PowerShell on Windows, bash on Unix).

    Parameters:
    - command: A single command (e.g., "dir", "python --version", "pip list").
      Command chaining/piping (";", "|", "&", "`", "$(...)") is NOT allowed.
    - timeout: Maximum execution time in seconds (default: 30, max: 300).
    - working_dir: Optional directory where command should run. If relative, resolved against home.

    Returns:
    A dictionary with status, output (stdout), error (stderr) if any.
    """
    # Validate timeout
    if not isinstance(timeout, int) or timeout < 1:
        timeout = 30
    timeout = min(timeout, 300)

    # SECURITY FIX: reject chained/piped commands outright. Previously only
    # the first token was checked against the whitelist, but the FULL raw
    # string was passed to the shell — so "dir; Remove-Item -Recurse C:\"
    # would pass the check on "dir" and then execute the destructive part
    # anyway. Blocking these characters closes that bypass.
    if _SHELL_METACHARACTERS.search(command):
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
    whitelist = _get_whitelist()
    if base_command not in whitelist:
        return {
            "status": "error",
            "error": f"Command '{base_command}' is not allowed. Allowed commands: {', '.join(whitelist)}",
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
