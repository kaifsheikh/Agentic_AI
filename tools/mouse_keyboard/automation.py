import json
import logging
import time
import functools
from typing import Optional, Tuple
import pyautogui
from langchain_core.tools import tool
from tools.utils import _resolve_path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# PyAutoGUI failsafe: Mouse ko screen ke corner (0,0) par le jane se program abort ho jata hai
pyautogui.FAILSAFE = True  # Default True, safety ke liye enable rakhein

# ============================================================
# Helper Decorator for Error Handling
# ============================================================
def _handle_errors(func):
    """Standard error handling for automation tools."""
    @functools.wraps(func)  # Preserves original signature so @tool builds a correct schema
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            logger.info(f"Tool '{func.__name__}' executed successfully.")
            if isinstance(result, dict):
                return json.dumps({"status": "success", **result}, default=str)
            return json.dumps({"status": "success", "message": str(result)})
        except pyautogui.FailSafeException:
            logger.warning(f"Tool '{func.__name__}' - failsafe triggered.")
            return json.dumps({"status": "error", "error": "Failsafe triggered: mouse moved to corner.", "error_type": "failsafe"})
        except (TypeError, ValueError) as e:
            logger.error(f"Tool '{func.__name__}' - invalid input: {e}")
            return json.dumps({"status": "error", "error": str(e), "error_type": "invalid_input"})
        except Exception as e:
            logger.error(f"Tool '{func.__name__}' - unexpected error: {e}")
            return json.dumps({"status": "error", "error": str(e), "error_type": "unknown"})
    return wrapper

# ============================================================
# Mouse Movement and Clicking
# ============================================================
@tool
@_handle_errors
def move_mouse(x: int, y: int, duration: float = 0.5) -> dict:
    """
    Mouse cursor ko specified screen coordinates (x, y) par smoothly move karein.
    
    Parameters:
    - x, y: Target coordinates (integers, pixel values)
    - duration: Movement time in seconds (default: 0.5). 0 = instant.
    
    Note: PyAutoGUI failsafe enabled hai - mouse ko top-left corner (0,0) par le jane se action abort ho jayega.
    """
    # Validate coordinates
    if not isinstance(x, int) or not isinstance(y, int):
        raise ValueError("x and y must be integers")
    if x < 0 or y < 0:
        raise ValueError("Coordinates must be non-negative")
    if not isinstance(duration, (int, float)) or duration < 0:
        raise ValueError("duration must be non-negative number")
    
    pyautogui.moveTo(x, y, duration=duration)
    return {"message": f"Mouse moved to ({x}, {y})"}

@tool
@_handle_errors
def click_mouse(x: Optional[int] = None, y: Optional[int] = None, 
                button: str = "left", clicks: int = 1, interval: float = 0.0) -> dict:
    """
    Mouse se click karein. Agar x, y diye gaye hain to wahan click, warna current position par.
    
    Parameters:
    - x, y: Optional coordinates (integers). If None, current position use hoti hai.
    - button: 'left', 'right', 'middle' (default: 'left')
    - clicks: Number of clicks (1 = single, 2 = double, etc.)
    - interval: Delay between clicks (seconds, only if clicks > 1)
    """
    # Validate
    if x is not None and y is not None:
        if not isinstance(x, int) or not isinstance(y, int):
            raise ValueError("x and y must be integers when provided")
    elif x is not None or y is not None:
        raise ValueError("Both x and y must be provided together, or neither")
    
    valid_buttons = {"left", "right", "middle"}
    if button not in valid_buttons:
        raise ValueError(f"Invalid button '{button}'. Must be one of {valid_buttons}")
    if not isinstance(clicks, int) or clicks < 1:
        raise ValueError("clicks must be positive integer")
    if not isinstance(interval, (int, float)) or interval < 0:
        raise ValueError("interval must be non-negative number")
    
    if x is not None and y is not None:
        pyautogui.click(x, y, clicks=clicks, interval=interval, button=button)
    else:
        pyautogui.click(clicks=clicks, interval=interval, button=button)
    
    return {"message": f"Click performed: button={button}, clicks={clicks}"}

@tool
@_handle_errors
def double_click(x: Optional[int] = None, y: Optional[int] = None, button: str = "left") -> dict:
    """
    Double click karein. Agar coordinates diye gaye hain to wahan, warna current position par.
    """
    if x is not None and y is not None:
        if not isinstance(x, int) or not isinstance(y, int):
            raise ValueError("x and y must be integers when provided")
        pyautogui.doubleClick(x, y, button=button)
    else:
        pyautogui.doubleClick(button=button)
    return {"message": "Double click performed"}

@tool
@_handle_errors
def drag_mouse(start_x: int, start_y: int, end_x: int, end_y: int, 
               duration: float = 1.0, button: str = "left") -> dict:
    """
    Mouse se drag karein from (start_x, start_y) to (end_x, end_y).
    Useful for selecting text or moving windows.
    """
    if not all(isinstance(v, int) for v in [start_x, start_y, end_x, end_y]):
        raise ValueError("All coordinates must be integers")
    if duration < 0:
        raise ValueError("duration must be non-negative")
    
    pyautogui.moveTo(start_x, start_y)
    pyautogui.dragTo(end_x, end_y, duration=duration, button=button)
    return {"message": f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})"}

# ============================================================
# Keyboard Actions
# ============================================================
@tool
@_handle_errors
def type_text(text: str, interval: float = 0.0) -> dict:
    """
    Keyboard se text type karein (current focused window mein).
    
    Parameters:
    - text: String to type
    - interval: Delay between each character (seconds), useful for slower typing
    """
    if not isinstance(text, str):
        raise ValueError("text must be string")
    if not isinstance(interval, (int, float)) or interval < 0:
        raise ValueError("interval must be non-negative number")
    
    pyautogui.write(text, interval=interval)
    return {"message": f"Typed text ({len(text)} characters)"}

@tool
@_handle_errors
def press_key(key: str) -> dict:
    """
    Koi specific key press karein, jaise 'enter', 'tab', 'ctrl', 'alt', 'space', 'a', 'F1', etc.
    """
    if not isinstance(key, str) or not key:
        raise ValueError("key must be non-empty string")
    
    # Optional: Validate against known key names? Could be too restrictive; leave as is.
    pyautogui.press(key)
    return {"message": f"Key pressed: {key}"}

@tool
@_handle_errors
def hotkey(keys: str) -> dict:
    """
    Multiple keys ek saath press karein, comma separated.
    Example: 'ctrl,c' ya 'alt,tab' ya 'ctrl,shift,esc'.
    """
    if not isinstance(keys, str):
        raise ValueError("keys must be string")
    key_list = [k.strip().lower() for k in keys.split(",") if k.strip()]
    if not key_list:
        raise ValueError("No keys provided")
    
    pyautogui.hotkey(*key_list)
    return {"message": f"Hotkey pressed: {', '.join(key_list)}"}

# ============================================================
# Screen Interaction
# ============================================================
@tool
@_handle_errors
def screenshot(save_path: str = "screenshot.png") -> dict:
    """
    Screen ka screenshot lekar file mein save karein.
    save_path optional, default current directory mein screenshot.png (home directory relative).
    """
    if not isinstance(save_path, str):
        raise ValueError("save_path must be string")
    
    img = pyautogui.screenshot()
    # Resolve path (home directory relative if not absolute)
    target_path = _resolve_path(save_path)
    # Ensure parent directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(target_path)
    return {"message": f"Screenshot saved at {target_path}", "path": str(target_path)}

@tool
@_handle_errors
def get_mouse_position() -> dict:
    """
    Current mouse cursor position (x, y) return karein.
    """
    pos = pyautogui.position()
    return {"x": pos.x, "y": pos.y}

@tool
@_handle_errors
def get_screen_size() -> dict:
    """
    Current screen resolution (width x height) return karein.
    """
    width, height = pyautogui.size()
    return {"width": width, "height": height}

@tool
@_handle_errors
def scroll_mouse(amount: int, x: Optional[int] = None, y: Optional[int] = None) -> dict:
    """
    Mouse scroll karein. Positive amount upar, negative neeche.
    Agar x, y diye gaye hain, to pehle wahan move karein phir scroll karein.
    """
    if not isinstance(amount, int):
        raise ValueError("amount must be integer")
    if x is not None and y is not None:
        if not isinstance(x, int) or not isinstance(y, int):
            raise ValueError("x and y must be integers when provided")
        pyautogui.moveTo(x, y)
    elif x is not None or y is not None:
        raise ValueError("Both x and y must be provided together")
    
    pyautogui.scroll(amount)
    return {"message": f"Scrolled by {amount}"}

# ============================================================
# Additional Utility (Optional)
# ============================================================
@tool
@_handle_errors
def move_and_click(x: int, y: int, button: str = "left") -> dict:
    """
    Mouse ko (x, y) par move karke click karein (shortcut for move + click).
    """
    if not isinstance(x, int) or not isinstance(y, int):
        raise ValueError("x and y must be integers")
    pyautogui.click(x, y, button=button)
    return {"message": f"Moved and clicked at ({x}, {y})"}
