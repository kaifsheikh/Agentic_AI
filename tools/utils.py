import ast
import functools
import json
import operator
import os
import logging
from pathlib import Path
from typing import Optional, List, Union

logger = logging.getLogger(__name__)

# ============================================================
# Path Resolution with Security (single source of truth —
# file_ops.py and system.py both import from here now, instead
# of each keeping their own copy of this logic)
# ============================================================

def _get_allowed_roots() -> List[str]:
    """
    Returns list of directories where file operations are permitted.
    Default: Home, Desktop, Documents, Downloads.
    Additional roots can be added via environment variable ALLOWED_ROOTS (comma-separated).
    """
    home = Path.home()
    default_roots = [
        str(home),
        str(home / "Desktop"),
        str(home / "Documents"),
        str(home / "Downloads"),
    ]
    custom = os.getenv("ALLOWED_ROOTS", "")
    if custom:
        for part in custom.split(","):
            part = part.strip()
            if part:
                p = Path(part).expanduser()
                if not p.is_absolute():
                    p = home / p
                default_roots.append(str(p.resolve()))
    return default_roots


def _resolve_path(path_str: str, must_exist: bool = False) -> Path:
    """
    Resolve a path string to an absolute Path object with security checks.

    - Expands ~ to user home.
    - If relative, assumes relative to user home directory.
    - Resolves symlinks and '..' to get real path.
    - Checks that the resolved path is within allowed roots.
    - Optionally checks that the path exists (if must_exist=True).

    Raises:
        PermissionError: If path is outside allowed roots.
        FileNotFoundError: If must_exist=True and path does not exist.
    """
    try:
        p = Path(path_str).expanduser()
        if not p.is_absolute():
            p = Path.home() / p

        target = p.resolve()

        allowed_roots = _get_allowed_roots()
        target_str = str(target)
        if not any(target_str == root or target_str.startswith(root + os.sep) for root in allowed_roots):
            raise PermissionError(f"Access denied: '{target}' is outside allowed directories.")

        if must_exist and not target.exists():
            raise FileNotFoundError(f"Path not found: {target}")

        logger.debug(f"Resolved path: {path_str} -> {target}")
        return target
    except PermissionError as e:
        logger.error(f"Permission denied for path '{path_str}': {e}")
        raise
    except FileNotFoundError as e:
        logger.warning(f"Path not found: {e}")
        raise
    except Exception as e:
        logger.error(f"Error resolving path '{path_str}': {e}")
        raise ValueError(f"Invalid path: {path_str}") from e


# ============================================================
# Shared error-handling decorators
# ============================================================

def handle_file_errors(func):
    """
    Standard error handling for file_ops-style tools.
    Wraps a dict result with {"status": "success", ...} and serializes to JSON.
    """
    @functools.wraps(func)
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


def handle_command_errors(func):
    """
    Standard error handling for system-command-style tools.
    The wrapped function is expected to already return a dict containing "status".
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        import subprocess
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
# Safe Mathematical Expression Evaluator
# ============================================================

def _safe_eval_expr(expr: str) -> Union[int, float]:
    """
    Safely evaluate a mathematical expression containing only numbers and basic operators.
    No variables, functions, or attribute access are allowed.
    """
    if not isinstance(expr, str):
        raise ValueError("Expression must be a string.")
    expr = expr.strip()
    if not expr:
        raise ValueError("Expression cannot be empty.")
    if len(expr) > 200:
        raise ValueError("Expression too long (max 200 characters).")

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
            if isinstance(node, ast.Expression):
                continue
            elif isinstance(node, ast.BinOp):
                if type(node.op) not in allowed_ops:
                    raise ValueError(f"Operator not allowed: {type(node.op).__name__}")
            elif isinstance(node, ast.UnaryOp):
                if type(node.op) not in allowed_ops:
                    raise ValueError(f"Unary operator not allowed: {type(node.op).__name__}")
            elif isinstance(node, ast.Constant):
                if not isinstance(node.value, (int, float)) or isinstance(node.value, bool):
                    raise ValueError("Only numeric literals are allowed.")
            elif isinstance(node, ast.Load):
                raise ValueError("Variables and names are not allowed.")
            elif isinstance(node, ast.Name):
                raise ValueError("Variables and names are not allowed.")
            else:
                raise ValueError(f"Invalid expression component: {type(node).__name__}")

        result = eval(compile(tree, filename='', mode='eval'), {"__builtins__": {}}, {})

        if isinstance(result, complex):
            raise ValueError("Complex numbers are not supported.")
        if not isinstance(result, (int, float)):
            raise ValueError(f"Unexpected result type: {type(result).__name__}")

        logger.debug(f"Evaluated expression '{expr}' = {result}")
        return result
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError) as e:
        logger.warning(f"Invalid expression '{expr}': {e}")
        raise ValueError(f"Invalid expression: {e}")
    except Exception as e:
        logger.error(f"Unexpected error evaluating '{expr}': {e}")
        raise ValueError(f"Error evaluating expression: {e}")


# ============================================================
# Misc shared utilities
# ============================================================

def _format_size(size_bytes: int) -> str:
    """Convert bytes to human-readable format."""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.2f} {units[i]}"
