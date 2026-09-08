import ast
import operator
from pathlib import Path

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