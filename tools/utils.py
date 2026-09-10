import ast
import operator
import os
import logging
from pathlib import Path
from typing import Optional, List, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ============================================================
# Path Resolution with Security
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
    # Add custom roots from env
    custom = os.getenv("ALLOWED_ROOTS", "")
    if custom:
        for part in custom.split(","):
            part = part.strip()
            if part:
                # Expand ~ and make absolute
                p = Path(part).expanduser()
                if not p.is_absolute():
                    p = home / p
                default_roots.append(str(p.resolve()))
    # Remove duplicates and ensure strings end with separator for startswith check
    # We'll keep as is; startswith will be used with string paths.
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
    
    Returns:
        Path object of the resolved path.
    """
    try:
        # Expand user home and make absolute
        p = Path(path_str).expanduser()
        if not p.is_absolute():
            p = Path.home() / p
        
        # Resolve to remove symlinks and '..'
        target = p.resolve()
        
        # Check if within allowed roots
        allowed_roots = _get_allowed_roots()
        target_str = str(target)
        if not any(target_str == root or target_str.startswith(root + os.sep) for root in allowed_roots):
            raise PermissionError(f"Access denied: '{target}' is outside allowed directories.")
        
        # Optionally check existence
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
# Safe Mathematical Expression Evaluator
# ============================================================

def _safe_eval_expr(expr: str) -> Union[int, float]:
    """
    Safely evaluate a mathematical expression containing only numbers and basic operators.
    No variables, functions, or attribute access are allowed.
    
    Allowed operators: +, -, *, /, //, %, **, unary +, unary -.
    Allowed values: integers, floats.
    
    Returns result as int or float, or raises ValueError.
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
        # Parse the expression
        tree = ast.parse(expr, mode='eval')
        
        # Walk through all nodes and validate
        for node in ast.walk(tree):
            # Check node types
            if isinstance(node, ast.Expression):
                continue
            elif isinstance(node, ast.BinOp):
                if type(node.op) not in allowed_ops:
                    raise ValueError(f"Operator not allowed: {type(node.op).__name__}")
            elif isinstance(node, ast.UnaryOp):
                if type(node.op) not in allowed_ops:
                    raise ValueError(f"Unary operator not allowed: {type(node.op).__name__}")
            elif isinstance(node, ast.Constant):
                # Only allow numbers (int, float), not strings, booleans, None, etc.
                if not isinstance(node.value, (int, float)) or isinstance(node.value, bool):
                    raise ValueError("Only numeric literals are allowed.")
            elif isinstance(node, ast.Load):
                # ast.Load is part of variable names, but we shouldn't have any names
                # Actually ast.Name nodes will be caught here; we disallow all Name nodes
                raise ValueError("Variables and names are not allowed.")
            elif isinstance(node, ast.Name):
                raise ValueError("Variables and names are not allowed.")
            else:
                # Reject any other node types (Calls, Attributes, etc.)
                raise ValueError(f"Invalid expression component: {type(node).__name__}")
        
        # Evaluate in completely isolated namespace (no builtins)
        result = eval(compile(tree, filename='', mode='eval'), {"__builtins__": {}}, {})
        
        # Ensure result is a number (int/float) and not complex
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
# Optional: Additional shared utilities
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