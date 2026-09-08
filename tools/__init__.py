from langchain_core.tools import BaseTool

# Import all tool functions
from tools.math.calculator import calculate
from tools.file_ops.file_ops import (
    create_file,
    read_file,
    list_folder_files,
    delete_file,
    delete_folder,
    copy_file,
    copy_folder,
    create_folder
)
from tools.system.system import execute_system_command
from tools.mouse_keyboard.automation import (
    move_mouse,
    click_mouse,
    type_text,
    press_key,
    hotkey,
    screenshot,
    get_mouse_position,
    scroll_mouse
)
from tools.email.email_tools import search_emails

def get_all_tools():
    """
    Is module (tools package) ke andar jitne bhi @tool decorated functions hain,
    un sab ko collect karke list return karta hai.
    """
    # Saare tool objects ki list explicitly return karo
    return [
        calculate,
        create_file,
        read_file,
        list_folder_files,
        delete_file,
        delete_folder,
        copy_file,
        copy_folder,
        create_folder,
        execute_system_command,
        move_mouse,
        click_mouse,
        type_text,
        press_key,
        hotkey,
        screenshot,
        get_mouse_position,
        scroll_mouse,
        search_emails,
    ]