import json
import subprocess
from langchain_core.tools import tool

@tool
def execute_system_command(command: str) -> str:
    """
    Execute a system command via PowerShell on Windows.
    Only a set of safe/whitelisted commands are allowed.
    (Blocklist removed as per user request)
    """
    whitelist = [
        "ipconfig", "dir", "cd", "echo", "start", "notepad", "calc", 
        "mspaint", "explorer", "tasklist", "systeminfo", "hostname",
        "ping", "tracert", "nslookup", "get-date", "get-process",
        "code", "python", "node", "activate", "call", "pip" , "tree"
    ]
    
    cmd_lower = command.lower().strip()
    
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