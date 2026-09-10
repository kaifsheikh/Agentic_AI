import json
import logging
import functools
from typing import Any
from langchain_core.tools import tool
from tools.utils import _safe_eval_expr

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ============================================================
# Helper Decorator for Error Handling
# ============================================================
def _handle_errors(func):
    """Standard error handling for calculator tool."""
    @functools.wraps(func)  # Preserves original signature so @tool builds a correct schema
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
    # Validate input
    if not isinstance(expression, str):
        raise ValueError("Expression must be a string.")
    expression = expression.strip()
    if not expression:
        raise ValueError("Expression cannot be empty.")
    if len(expression) > 200:
        raise ValueError("Expression too long (max 200 characters).")

    # Evaluate using the safe evaluator
    result = _safe_eval_expr(expression)

    # Convert result to a JSON-serializable type if needed
    if isinstance(result, (int, float)):
        # Ensure no complex numbers or unsupported types
        if isinstance(result, complex):
            raise ValueError("Complex numbers are not supported.")
        return {"result": result}
    else:
        raise ValueError(f"Unexpected result type: {type(result).__name__}")

    # Note: _safe_eval_expr should already raise exceptions on invalid expressions.
