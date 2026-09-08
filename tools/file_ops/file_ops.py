import json
import os
import shutil
from pathlib import Path
from langchain_core.tools import tool
from tools.utils import _resolve_path

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