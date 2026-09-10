import json
import os
import shutil
import fnmatch
import logging
import functools
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from langchain_core.tools import tool

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ============================================================
# Safe Path Resolution with Configurable Root
# ============================================================
ALLOWED_ROOTS = [
    str(Path.home()),                    # User home directory
    str(Path.home() / "Desktop"),        # Desktop
    str(Path.home() / "Documents"),      # Documents
    str(Path.home() / "Downloads"),      # Downloads
]

def _resolve_path(file_path: str, must_exist: bool = False) -> Path:
    """
    Resolve a path safely, preventing path traversal attacks.
    If path is relative, it's resolved against the user's home directory.
    """
    try:
        raw_path = Path(file_path)
        if not raw_path.is_absolute():
            target = Path.home() / raw_path
        else:
            target = raw_path

        target = target.resolve()  # Resolve symlinks and ..
        
        # Check if path is within allowed roots.
        # Fixed: compare against root or "root + separator" so a sibling folder
        # that merely starts with the same characters (e.g. "...\DELL5420Evil")
        # can no longer slip past the check.
        target_str = str(target)
        if not any(
            target_str == root or target_str.startswith(root + os.sep)
            for root in ALLOWED_ROOTS
        ):
            raise PermissionError(f"Access denied: '{target}' is outside allowed directories.")
        
        if must_exist and not target.exists():
            raise FileNotFoundError(f"Path not found: {target}")
        
        return target
    except Exception as e:
        logger.error(f"Path resolution failed for '{file_path}': {e}")
        raise


# ============================================================
# Helper Decorator for Standard Error Handling
# ============================================================
def _handle_errors(func):
    """Wrapper to standardize error handling across all tools."""
    @functools.wraps(func)  # Preserves original signature so @tool builds a correct schema
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            logger.info(f"Tool '{func.__name__}' executed successfully.")
            return json.dumps({"status": "success", **result}, default=str)
        except FileNotFoundError as e:
            logger.warning(f"Tool '{func.__name__}' - not found: {e}")
            return json.dumps({"status": "error", "error": str(e), "error_type": "not_found"})
        except PermissionError as e:
            logger.error(f"Tool '{func.__name__}' - permission denied: {e}")
            return json.dumps({"status": "error", "error": str(e), "error_type": "permission_denied"})
        except Exception as e:
            logger.error(f"Tool '{func.__name__}' - unexpected error: {e}")
            return json.dumps({"status": "error", "error": str(e), "error_type": "unknown"})
    return wrapper


# ============================================================
# FILE CREATION & WRITING
# ============================================================
@tool
@_handle_errors
def create_file(file_path: str, content: str = "") -> dict:
    """
    Create a file at the specified path with given content.
    If parent directories don't exist, they will be created automatically.
    """
    target = _resolve_path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    
    # Don't overwrite existing file without warning
    if target.exists():
        return {
            "warning": f"File already exists at {target}, not overwriting.",
            "message": "Use 'write_file' to overwrite existing file."
        }
    
    target.write_text(content, encoding="utf-8")
    return {"message": f"File created successfully at: {target}"}


@tool
@_handle_errors
def write_file(file_path: str, content: str) -> dict:
    """
    Write content to a file, overwriting if it exists.
    """
    target = _resolve_path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"message": f"File written successfully at: {target}"}


@tool
@_handle_errors
def append_file(file_path: str, content: str) -> dict:
    """
    Append content to the end of an existing file.
    Creates the file if it doesn't exist.
    """
    target = _resolve_path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "a", encoding="utf-8") as f:
        f.write(content)
    return {"message": f"Content appended successfully to: {target}"}


@tool
@_handle_errors
def write_json(file_path: str, data: dict) -> dict:
    """
    Write a Python dictionary as JSON to a file.
    """
    target = _resolve_path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return {"message": f"JSON data written to: {target}"}


# ============================================================
# FILE READING
# ============================================================
@tool
@_handle_errors
def read_file(file_path: str, max_chars: Optional[int] = 10000) -> dict:
    """
    Read the content of a file.
    max_chars: Maximum characters to read (default: 10000). Set to None for full file.
    """
    target = _resolve_path(file_path, must_exist=True)
    
    if not target.is_file():
        raise FileNotFoundError(f"Not a file: {target}")
    
    content = target.read_text(encoding="utf-8")
    
    if max_chars and len(content) > max_chars:
        content = content[:max_chars] + f"\n... [TRUNCATED - {len(content) - max_chars} more chars]"
    
    return {"content": content, "file_size": target.stat().st_size, "path": str(target)}


@tool
@_handle_errors
def read_json(file_path: str) -> dict:
    """
    Read a JSON file and return its contents as a Python dictionary.
    """
    target = _resolve_path(file_path, must_exist=True)
    
    with open(target, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return {"data": data, "path": str(target)}


@tool
@_handle_errors
def read_file_lines(file_path: str, start_line: int = 1, end_line: Optional[int] = None) -> dict:
    """
    Read specific lines from a file.
    start_line: First line to read (1-indexed).
    end_line: Last line to read (inclusive). If None, reads till end.
    """
    target = _resolve_path(file_path, must_exist=True)
    
    with open(target, "r", encoding="utf-8") as f:
        all_lines = f.readlines()
    
    total_lines = len(all_lines)
    start_idx = max(0, start_line - 1)
    end_idx = total_lines if end_line is None else min(total_lines, end_line)
    
    selected_lines = all_lines[start_idx:end_idx]
    
    return {
        "lines": selected_lines,
        "line_range": f"{start_idx + 1}-{end_idx}",
        "total_lines": total_lines
    }


# ============================================================
# FILE & FOLDER LISTING
# ============================================================
@tool
@_handle_errors
def list_folder_files(folder_path: str = None, include_hidden: bool = False) -> dict:
    """
    List all files and sub-folders inside a directory.
    If folder_path is not provided, defaults to the user's Desktop/Agentic_ai folder.
    include_hidden: Whether to include hidden files/folders (starting with dot).
    """
    # Default path agar user ne nahi diya
    if folder_path is None or (isinstance(folder_path, str) and folder_path.strip() == ""):
        folder_path = str(Path.home() / "Desktop" / "python" / "Agentic_AI")
    
    target = _resolve_path(folder_path, must_exist=True)
    
    if not target.is_dir():
        raise FileNotFoundError(f"Not a directory: {target}")
    
    items = []
    for item in target.iterdir():
        if not include_hidden and item.name.startswith('.'):
            continue
        items.append({
            "name": item.name,
            "type": "folder" if item.is_dir() else "file",
            "size": item.stat().st_size if item.is_file() else None,
            "modified": datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return {"items": items, "count": len(items), "path": str(target)}


@tool
@_handle_errors
def search_files(directory: str, pattern: str = "*", recursive: bool = True) -> dict:
    """
    Search for files matching a pattern (glob style).
    pattern: e.g., "*.txt", "*.py", "data*", etc.
    recursive: Search in sub-directories too.
    """
    target = _resolve_path(directory, must_exist=True)
    
    if not target.is_dir():
        raise FileNotFoundError(f"Not a directory: {target}")
    
    matches = []
    if recursive:
        for root, dirs, files in os.walk(target):
            for filename in fnmatch.filter(files, pattern):
                full_path = Path(root) / filename
                matches.append({
                    "name": filename,
                    "path": str(full_path),
                    "size": full_path.stat().st_size
                })
            # Also match directories if pattern matches
            for dirname in fnmatch.filter(dirs, pattern):
                matches.append({
                    "name": dirname,
                    "path": str(Path(root) / dirname),
                    "type": "folder"
                })
    else:
        for item in target.iterdir():
            if fnmatch.fnmatch(item.name, pattern):
                matches.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "folder" if item.is_dir() else "file"
                })
    
    return {"matches": matches, "count": len(matches), "pattern": pattern}


# ============================================================
# FILE INFORMATION
# ============================================================
@tool
@_handle_errors
def get_file_info(file_path: str) -> dict:
    """
    Get detailed information about a file or folder.
    """
    target = _resolve_path(file_path, must_exist=True)
    stat = target.stat()
    
    info = {
        "name": target.name,
        "path": str(target),
        "type": "folder" if target.is_dir() else "file",
        "size_bytes": stat.st_size,
        "size_human": _format_size(stat.st_size),
        "created": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "permissions": oct(stat.st_mode)[-3:],
    }
    
    if target.is_dir():
        info["items_count"] = len(list(target.iterdir()))
    
    return {"info": info}


# ============================================================
# FILE MOVING & RENAMING
# ============================================================
@tool
@_handle_errors
def move_file(source_path: str, destination_path: str) -> dict:
    """
    Move a file to a new location. Can also be used for renaming.
    """
    src = _resolve_path(source_path, must_exist=True)
    
    if not src.is_file():
        raise FileNotFoundError(f"Not a file: {src}")
    
    dst = _resolve_path(destination_path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    
    # If destination is a directory, append source filename
    if dst.is_dir():
        dst = dst / src.name
    
    shutil.move(str(src), str(dst))
    return {"message": f"File moved from {src} to {dst}"}


@tool
@_handle_errors
def move_folder(source_folder: str, destination_folder: str) -> dict:
    """
    Move an entire folder to a new location. Can also be used for renaming.
    """
    src = _resolve_path(source_folder, must_exist=True)
    
    if not src.is_dir():
        raise FileNotFoundError(f"Not a folder: {src}")
    
    dst = _resolve_path(destination_folder)
    dst.parent.mkdir(parents=True, exist_ok=True)
    
    shutil.move(str(src), str(dst))
    return {"message": f"Folder moved from {src} to {dst}"}


# ============================================================
# DELETION
# ============================================================
@tool
@_handle_errors
def delete_file(file_path: str) -> dict:
    """
    Delete a specific file.
    """
    target = _resolve_path(file_path, must_exist=True)
    
    if not target.is_file():
        raise FileNotFoundError(f"Not a file: {target}")
    
    target.unlink()
    return {"message": f"File deleted: {target}"}


@tool
@_handle_errors
def delete_folder(folder_path: str) -> dict:
    """
    Delete a folder and all its contents recursively.
    WARNING: This operation is irreversible!
    """
    target = _resolve_path(folder_path, must_exist=True)
    
    if not target.is_dir():
        raise FileNotFoundError(f"Not a folder: {target}")
    
    shutil.rmtree(target)
    return {"message": f"Folder deleted: {target}"}


# ============================================================
# COPYING
# ============================================================
@tool
@_handle_errors
def copy_file(source_path: str, destination_path: str) -> dict:
    """
    Copy a single file to a new location.
    """
    src = _resolve_path(source_path, must_exist=True)
    
    if not src.is_file():
        raise FileNotFoundError(f"Not a file: {src}")
    
    dst = _resolve_path(destination_path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    
    if dst.is_dir():
        dst = dst / src.name
    
    shutil.copy2(str(src), str(dst))
    return {"message": f"File copied from {src} to {dst}"}


@tool
@_handle_errors
def copy_folder(source_folder: str, destination_folder: str) -> dict:
    """
    Copy an entire folder and its contents to a new location.
    """
    src = _resolve_path(source_folder, must_exist=True)
    
    if not src.is_dir():
        raise FileNotFoundError(f"Not a folder: {src}")
    
    dst = _resolve_path(destination_folder)
    dst.parent.mkdir(parents=True, exist_ok=True)
    
    shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
    return {"message": f"Folder copied from {src} to {dst}"}


# ============================================================
# FOLDER CREATION
# ============================================================
@tool
@_handle_errors
def create_folder(folder_path: str) -> dict:
    """
    Create a new folder (and any necessary parent folders).
    """
    target = _resolve_path(folder_path)
    
    if target.exists():
        return {"warning": f"Folder already exists: {target}", "message": "No action taken."}
    
    target.mkdir(parents=True, exist_ok=True)
    return {"message": f"Folder created: {target}"}


# ============================================================
# BULK OPERATIONS
# ============================================================
@tool
@_handle_errors
def create_multiple_files(files: List[dict]) -> dict:
    """
    Create multiple files at once.
    files: List of {"path": "..." , "content": "..."} objects.
    """
    created = []
    errors = []
    
    for file_spec in files:
        try:
            file_path = file_spec.get("path")
            content = file_spec.get("content", "")
            target = _resolve_path(file_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            created.append(str(target))
        except Exception as e:
            errors.append({"path": file_spec.get("path"), "error": str(e)})
    
    return {
        "created_count": len(created),
        "created_files": created,
        "errors": errors,
        "message": f"Created {len(created)} files, {len(errors)} errors."
    }


# ============================================================
# Helper Function
# ============================================================
def _format_size(size_bytes: int) -> str:
    """Convert bytes to human-readable format."""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {units[i]}"
