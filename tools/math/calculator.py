import json
import logging
import functools
from langchain_core.tools import tool
from tools.utils import _safe_eval_expr

logger = logging.getLogger(__name__)


# ============================================================
# Helper Decorator for Error Handling
# ============================================================
def _handle_errors(func):
    """Standard error handling for calculator tool."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return json.dumps({"status": "success", **result}, default=str)
        except ValueError as e:
            logger.warning(f"Invalid input: {e}")
            return json.dumps({"status": "error", "error": str(e), "error_type": "invalid_input"})
        except ArithmeticError as e:
            logger.error(f"Arithmetic error: {e}")
            return json.dumps({"status": "error", "error": str(e), "error_type": "arithmetic_error"})
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return json.dumps({"status": "error", "error": str(e), "error_type": "unknown"})
    return wrapper


# ============================================================
# Main Tool
# ============================================================
@tool
@_handle_errors
def calculate(expression: str) -> dict:
    """
    Evaluate a mathematical expression safely.
    Only numbers, +, -, *, /, //, %, **, parentheses are allowed.
    No functions or variables are permitted for security.

    Parameters:
    - expression: String containing the mathematical expression, e.g., '25 * 4 + 10'.

    Returns:
    A dictionary with 'result' (the evaluated number) on success.
    """
    if not isinstance(expression, str):
        raise ValueError("Expression must be a string.")
    expression = expression.strip()
    if not expression:
        raise ValueError("Expression cannot be empty.")
    if len(expression) > 200:
        raise ValueError("Expression too long (max 200 characters).")

    result = _safe_eval_expr(expression)

    if isinstance(result, complex):
        raise ValueError("Complex numbers are not supported.")
    if not isinstance(result, (int, float)):
        raise ValueError(f"Unexpected result type: {type(result).__name__}")

    return {"result": result}
