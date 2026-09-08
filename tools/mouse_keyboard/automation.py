import json
import time
import pyautogui
from langchain_core.tools import tool
from tools.utils import _resolve_path

@tool
def move_mouse(x: int, y: int, duration: float = 0.5) -> str:
    """
    Mouse cursor ko specified screen coordinates (x, y) par move karein.
    duration optional hai (seconds).
    """
    try:
        pyautogui.moveTo(x, y, duration=duration)
        return json.dumps({"status": "success", "message": f"Mouse moved to ({x}, {y})"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

@tool
def click_mouse(x: int = None, y: int = None, button: str = "left") -> str:
    """
    Mouse se click karein. Agar x, y diye gaye hain to wahan click karein, warna current position par.
    button: 'left', 'right', 'middle'
    """
    try:
        if x is not None and y is not None:
            pyautogui.click(x, y, button=button)
        else:
            pyautogui.click(button=button)
        return json.dumps({"status": "success", "message": "Click performed"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

@tool
def type_text(text: str) -> str:
    """
    Keyboard se text type karein (current focused window mein).
    """
    try:
        pyautogui.write(text)
        return json.dumps({"status": "success", "message": f"Typed: {text}"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

@tool
def press_key(key: str) -> str:
    """
    Koi specific key press karein, jaise 'enter', 'tab', 'ctrl', 'alt', etc.
    """
    try:
        pyautogui.press(key)
        return json.dumps({"status": "success", "message": f"Key pressed: {key}"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

@tool
def hotkey(keys: str) -> str:
    """
    Multiple keys ek saath press karein, comma separated. Example: 'ctrl,c' ya 'alt,tab'.
    """
    try:
        key_list = [k.strip() for k in keys.split(",")]
        pyautogui.hotkey(*key_list)
        return json.dumps({"status": "success", "message": f"Hotkey pressed: {keys}"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

@tool
def screenshot(save_path: str = "screenshot.png") -> str:
    """
    Screen ka screenshot lekar file mein save karein.
    save_path optional hai, default current directory mein screenshot.png.
    """
    try:
        img = pyautogui.screenshot()
        # save_path ko resolve karein (home directory relative)
        target_path = _resolve_path(save_path)
        img.save(target_path)
        return json.dumps({"status": "success", "message": f"Screenshot saved at {target_path}"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

@tool
def get_mouse_position() -> str:
    """
    Current mouse cursor position (x, y) return karein.
    """
    try:
        pos = pyautogui.position()
        return json.dumps({"status": "success", "x": pos.x, "y": pos.y})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

@tool
def scroll_mouse(amount: int) -> str:
    """
    Mouse scroll karein. Positive amount upar scroll, negative neeche.
    """
    try:
        pyautogui.scroll(amount)
        return json.dumps({"status": "success", "message": f"Scrolled by {amount}"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})