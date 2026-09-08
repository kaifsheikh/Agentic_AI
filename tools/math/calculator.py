import json
from langchain_core.tools import tool
from tools.utils import _safe_eval_expr

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