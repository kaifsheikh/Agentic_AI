import os
import shutil
import fnmatch
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from langchain_core.tools import tool

from tools.utils import _resolve_path, _format_size, handle_file_errors

logger = logging.getLogger(__name__)


# ============================================================
# FILE CREATION & WRITING
# ============================================================
@tool
@handle_file_errors
def create_file(file_path: str, content: str = "") -> dict:
    """
    Create a file at the specified path with given content.
    If parent directories don't exist, they will be created automatically.
    """
    target = _resolve_path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        return {
            "warning": f"File already exists at {target}, not overwriting.",
            "message": "Use 'write_file' to overwrite existing file."
        }

    target.write_text(content, encoding="utf-8")
    return {"message": f"File created successfully at: {target}"}


@tool
@handle_file_errors
def write_file(file_path: str, content: str) -> dict:
    """
    Write content to a file, overwriting if it exists.
    """
    target = _resolve_path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"message": f"File written successfully at: {target}"}


@tool
@handle_file_errors
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
@handle_file_errors
def write_json(file_path: str, data: dict) -> dict:
    """
    Write a Python dictionary as JSON to a file.
    """
    import json
    target = _resolve_path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return {"message": f"JSON data written to: {target}"}


# ============================================================
# FILE READING
# ============================================================
@tool
@handle_file_errors
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
@handle_file_errors
def read_json(file_path: str) -> dict:
    """
    Read a JSON file and return its contents as a Python dictionary.
    """
    import json
    target = _resolve_path(file_path, must_exist=True)

    with open(target, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {"data": data, "path": str(target)}


@tool
@handle_file_errors
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
@handle_file_errors
def list_folder_files(folder_path: str = None, include_hidden: bool = False) -> dict:
    """
    List all files and sub-folders inside a directory.
    If folder_path is not provided, defaults to the user's Agentic_AI project folder.
    include_hidden: Whether to include hidden files/folders (starting with dot).
    """
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
@handle_file_errors
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
@handle_file_errors
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
@handle_file_errors
def move_file(source_path: str, destination_path: str) -> dict:
    """
    Move a file to a new location. Can also be used for renaming.
    """
    src = _resolve_path(source_path, must_exist=True)

    if not src.is_file():
        raise FileNotFoundError(f"Not a file: {src}")

    dst = _resolve_path(destination_path)
    dst.parent.mkdir(parents=True, exist_ok=True)

    if dst.is_dir():
        dst = dst / src.name

    shutil.move(str(src), str(dst))
    return {"message": f"File moved from {src} to {dst}"}


@tool
@handle_file_errors
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
@handle_file_errors
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
@handle_file_errors
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
@handle_file_errors
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
@handle_file_errors
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
@handle_file_errors
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
@handle_file_errors
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
