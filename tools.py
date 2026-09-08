import json
import subprocess
import os
import shutil
import ast
import operator
from pathlib import Path
from langchain_core.tools import tool
import pyautogui
import time
from langchain_core.tools import BaseTool
import imaplib
import email
from email.header import decode_header

# ========== Helper Functions ==========

def _resolve_path(path_str: str) -> Path:
    """
    Resolves a path string to an absolute Path object.
    - Expands ~ to user home
    - If relative, assumes relative to user home directory
    """
    p = Path(path_str).expanduser()
    if not p.is_absolute():
        p = Path.home() / p
    return p

def _safe_eval_expr(expr: str):
    """
    Safely evaluate a mathematical expression containing only numbers and basic operators.
    Returns result or raises ValueError.
    """
    allowed_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }
    try:
        tree = ast.parse(expr, mode='eval')
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and type(node.op) not in allowed_ops:
                raise ValueError(f"Operator not allowed: {type(node.op).__name__}")
            elif isinstance(node, ast.UnaryOp) and type(node.op) not in allowed_ops:
                raise ValueError(f"Unary operator not allowed: {type(node.op).__name__}")
            elif isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
                raise ValueError("Only numeric literals are allowed")
            elif not isinstance(node, (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant)):
                raise ValueError("Invalid expression")
        # Evaluate in isolated namespace
        result = eval(compile(tree, filename='', mode='eval'), {"__builtins__": {}}, {})
        return result
    except Exception as e:
        raise ValueError(f"Invalid expression: {e}")

# ========== Tool Definitions ==========

# 1. Mathematical Calculation Tool
@tool
def calculate(expression: str) -> str:
    """
    Evaluate a mathematical expression.
    Only numbers, +, -, *, /, //, %, **, parentheses are allowed.
    Input: expression string, e.g., '25 * 4 + 10'
    """
    try:
        result = _safe_eval_expr(expression)
        return json.dumps({"result": result})
    except Exception as e:
        return json.dumps({"error": str(e)})

# 2. File Creation Tool
@tool
def create_file(file_path: str, content: str) -> str:
    """
    Create a file at the specified path with the given text content.
    If the path is relative, it will be created under the user's home directory.
    """
    try:
        target_path = _resolve_path(file_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(str(content))
        return json.dumps({
            "status": "success",
            "message": f"File successfully created at {target_path}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

# 3. File Read Tool
@tool
def read_file(file_path: str) -> str:
    """
    Read the text content of a file at the specified path.
    If the path is relative, it will be resolved against the user's home directory.
    """
    try:
        target_path = _resolve_path(file_path)
        if not target_path.exists():
            return json.dumps({"status": "error", "message": "File nahi mili."})
        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()
        return json.dumps({"status": "success", "content": content})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

# 4. Folder Files Listing Tool
@tool
def list_folder_files(folder_path: str) -> str:
    """
    List all files and sub-folders inside a directory.
    If the path is relative, it will be resolved against the user's home directory.
    """
    try:
        target_path = _resolve_path(folder_path)
        if not target_path.exists():
            return json.dumps({"status": "error", "message": "Folder nahi mila."})
        files_list = os.listdir(target_path)
        return json.dumps({"status": "success", "files": files_list})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

# 5. File Delete Tool
@tool
def delete_file(file_path: str) -> str:
    """
    Delete a specific file.
    If the path is relative, it will be resolved against the user's home directory.
    """
    try:
        target_path = _resolve_path(file_path)
        if not target_path.exists():
            return json.dumps({"status": "error", "message": f"File nahi mili: {target_path}"})
        if not target_path.is_file():
            return json.dumps({"status": "error", "message": "Yeh path ek file nahi hai (folder ho sakta hai)."})
        target_path.unlink()
        return json.dumps({
            "status": "success",
            "message": f"File successfully delete ho gayi: {target_path}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

# 6. Folder Delete Tool
@tool
def delete_folder(folder_path: str) -> str:
    """
    Delete a folder and all its contents recursively.
    If the path is relative, it will be resolved against the user's home directory.
    """
    try:
        target_path = _resolve_path(folder_path)
        if not target_path.exists():
            return json.dumps({"status": "error", "message": f"Folder nahi mila: {target_path}"})
        if not target_path.is_dir():
            return json.dumps({"status": "error", "message": "Yeh path ek folder nahi hai."})
        shutil.rmtree(target_path)
        return json.dumps({
            "status": "success",
            "message": f"Folder successfully delete ho gaya: {target_path}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

# 7. Single File Copy & Paste Tool
@tool
def copy_file(source_path: str, destination_path: str) -> str:
    """
    Copy a single file to a new location.
    - source_path: full path of the file to copy.
    - destination_path: full path of the target file OR an existing directory (then source filename is used).
    Relative paths are resolved against the user's home directory.
    """
    try:
        src = _resolve_path(source_path)
        dst = _resolve_path(destination_path)

        if not src.exists():
            return json.dumps({"status": "error", "message": f"Source file nahi mili: {src}"})
        if not src.is_file():
            return json.dumps({"status": "error", "message": "Source path file nahi hai."})

        # Determine final destination
        if dst.is_dir() or destination_path.endswith(("/", "\\")):
            # If destination is a directory or ends with slash, append source filename
            dst = dst / src.name
        else:
            # Treat destination as full file path; ensure parent directory exists
            dst.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(src, dst)
        return json.dumps({
            "status": "success",
            "message": f"File successfully copy ho gayi from {src} to {dst}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

# 8. Complete Folder Copy & Paste Tool
@tool
def copy_folder(source_folder: str, destination_folder: str) -> str:
    """
    Copy an entire folder and its contents to a new location.
    - source_folder: path of the folder to copy.
    - destination_folder: path where the folder will be copied (if exists, contents merged).
    Relative paths are resolved against the user's home directory.
    """
    try:
        src = _resolve_path(source_folder)
        dst = _resolve_path(destination_folder)

        if not src.exists():
            return json.dumps({"status": "error", "message": f"Source folder nahi mila: {src}"})
        if not src.is_dir():
            return json.dumps({"status": "error", "message": "Source path folder nahi hai."})

        shutil.copytree(src, dst, dirs_exist_ok=True)
        return json.dumps({
            "status": "success",
            "message": f"Folder successfully copy ho gaya from {src} to {dst}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

# 9. Create Folder Tool
@tool
def create_folder(folder_path: str) -> str:
    """
    Create a new folder (and any necessary parent folders).
    If the path is relative, it will be resolved against the user's home directory.
    """
    try:
        target_path = _resolve_path(folder_path)
        if target_path.exists():
            return json.dumps({
                "status": "info",
                "message": f"Folder pehle se majood hai: {target_path}"
            })
        target_path.mkdir(parents=True, exist_ok=True)
        return json.dumps({
            "status": "success",
            "message": f"Folder successfully create ho gaya at: {target_path}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

# 10. System Command Execution Tool
@tool
def execute_system_command(command: str) -> str:
    """
    Execute a system command using PowerShell on Windows.
    Use this for terminal commands, launching applications, or system configurations.
    NOTE: For safety, some high‑risk commands (like format, shutdown, del /s, rm -rf /) are blocked.
    """
    # Block dangerous commands (basic safety)
    dangerous_patterns = [
        "format",
        "shutdown",
        "restart",
        "del /s",
        "rm -rf /",
        "rmdir /s",
        "diskpart",
        "reg delete",
    ]
    cmd_lower = command.lower()
    for pattern in dangerous_patterns:
        if pattern in cmd_lower:
            return json.dumps({
                "status": "error",
                "error": f"Command blocked due to safety policy: '{pattern}'"
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

# ========== Mouse & Keyboard Automation Tools ==========

@tool
def move_mouse(x: int, y: int, duration: float = 0.5) -> str:
    """
    Mouse cursor ko specified screen coordinates (x, y) par move karein.
    duration optional hai (seconds).
    """
    try:
        pyautogui.moveTo(x, y, duration=duration)
        return json.dumps({"status": "success", "message": f"Mouse moved to ({x}, {y})"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

@tool
def click_mouse(x: int = None, y: int = None, button: str = "left") -> str:
    """
    Mouse se click karein. Agar x, y diye gaye hain to wahan click karein, warna current position par.
    button: 'left', 'right', 'middle'
    """
    try:
        if x is not None and y is not None:
            pyautogui.click(x, y, button=button)
        else:
            pyautogui.click(button=button)
        return json.dumps({"status": "success", "message": "Click performed"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

@tool
def type_text(text: str) -> str:
    """
    Keyboard se text type karein (current focused window mein).
    """
    try:
        pyautogui.write(text)
        return json.dumps({"status": "success", "message": f"Typed: {text}"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

@tool
def press_key(key: str) -> str:
    """
    Koi specific key press karein, jaise 'enter', 'tab', 'ctrl', 'alt', etc.
    """
    try:
        pyautogui.press(key)
        return json.dumps({"status": "success", "message": f"Key pressed: {key}"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

@tool
def hotkey(keys: str) -> str:
    """
    Multiple keys ek saath press karein, comma separated. Example: 'ctrl,c' ya 'alt,tab'.
    """
    try:
        key_list = [k.strip() for k in keys.split(",")]
        pyautogui.hotkey(*key_list)
        return json.dumps({"status": "success", "message": f"Hotkey pressed: {keys}"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

@tool
def screenshot(save_path: str = "screenshot.png") -> str:
    """
    Screen ka screenshot lekar file mein save karein.
    save_path optional hai, default current directory mein screenshot.png.
    """
    try:
        img = pyautogui.screenshot()
        # save_path ko resolve karein (home directory relative)
        target_path = _resolve_path(save_path)
        img.save(target_path)
        return json.dumps({"status": "success", "message": f"Screenshot saved at {target_path}"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

@tool
def get_mouse_position() -> str:
    """
    Current mouse cursor position (x, y) return karein.
    """
    try:
        pos = pyautogui.position()
        return json.dumps({"status": "success", "x": pos.x, "y": pos.y})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

@tool
def scroll_mouse(amount: int) -> str:
    """
    Mouse scroll karein. Positive amount upar scroll, negative neeche.
    """
    try:
        pyautogui.scroll(amount)
        return json.dumps({"status": "success", "message": f"Scrolled by {amount}"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

@tool
def search_emails(query: str, folder: str = "INBOX", limit: int = 5) -> str:
    """
    Search emails in the specified folder based on a query (sender name, subject, or keyword).
    Returns matching emails (sender, subject, date, snippet).
    """
    email_addr = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    imap_server = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")

    if not email_addr or not password:
        return json.dumps({"status": "error", "error": "Email credentials not set in .env"})

    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_addr, password)
        mail.select(folder)

        # Search criteria: FROM, SUBJECT, TEXT mein query dhoondo
        search_criteria = f'(OR (FROM "{query}") (SUBJECT "{query}") (TEXT "{query}"))'
        status, messages = mail.search(None, search_criteria)

        if status != "OK" or not messages[0]:
            return json.dumps({"status": "success", "output": f"'{query}' se koi email nahi mili."})

        email_ids = messages[0].split()[-limit:]
        result = []
        for e_id in email_ids:
            status, msg_data = mail.fetch(e_id, "(RFC822)")
            if status != "OK":
                continue
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8")

            sender = msg.get("From")
            date = msg.get("Date")

            body_snippet = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body_snippet = part.get_payload(decode=True).decode('utf-8', errors='ignore')[:200]
                        break
            else:
                body_snippet = msg.get_payload(decode=True).decode('utf-8', errors='ignore')[:200]

            result.append(f"From: {sender}\nSubject: {subject}\nDate: {date}\nSnippet: {body_snippet}\n---")

        mail.logout()
        return json.dumps({"status": "success", "output": "\n".join(result)})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

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

def get_all_tools():
    """
    Is module (tools.py) ke andar jitne bhi @tool decorated functions hain,
    un sab ko collect karke list return karta hai.
    """
    tools = []
    for name, obj in globals().items():
        if isinstance(obj, BaseTool):
            tools.append(obj)
    return tools

# Ek important baat: Memory tab tak rahegi jab tak aapka program chal raha hai (RAM mein). Agar aap program band karenge aur dobara chalayenge, to memory clear ho jayegi. Persistent memory ke liye aapko SQLite ya koi database checkpointer use karna hoga.