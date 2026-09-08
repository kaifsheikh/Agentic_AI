import json
import subprocess
from langchain_core.tools import tool

@tool
def execute_system_command(command: str) -> str:
    """
    Execute a system command via PowerShell on Windows.
    Only a set of safe/whitelisted commands are allowed.
    Danger commands are blocked.
    """
    # Whitelist of allowed command prefixes (lowercase)
    whitelist = [
        "ipconfig", "dir", "cd", "echo", "start", "notepad", "calc", 
        "mspaint", "explorer", "tasklist", "systeminfo", "hostname",
        "ping", "tracert", "nslookup", "get-date", "get-process"
    ]
    
    # Dangerous patterns to block (even if whitelist me na ho)
    blocklist = [
        "format", "shutdown", "restart", "del /s", "rmdir /s", "rm -rf",
        "diskpart", "reg delete", "stop-computer", "restart-computer"
    ]
    
    cmd_lower = command.lower().strip()
    
    # Check blocklist first
    for pattern in blocklist:
        if pattern in cmd_lower:
            return json.dumps({
                "status": "error",
                "error": f"Command blocked due to safety policy: '{pattern}'"
            })
    
    # Check whitelist: command should start with one of the allowed prefixes
    allowed = False
    for prefix in whitelist:
        if cmd_lower.startswith(prefix):
            allowed = True
            break
    if not allowed:
        return json.dumps({
            "status": "error",
            "error": f"Command not allowed. Only safe commands like: {', '.join(whitelist)}"
        })
    
    try:
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return json.dumps({"status": "success", "output": result.stdout.strip()})
        else:
            return json.dumps({"status": "error", "error": result.stderr.strip()})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})