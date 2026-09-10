from langchain_core.tools import BaseTool

# Import all tool functions (professional versions)
from tools.math.calculator import calculate

# File operations (expanded)
from tools.file_ops.file_ops import (
    create_file,
    write_file,
    append_file,
    write_json,
    read_file,
    read_json,
    read_file_lines,
    list_folder_files,
    search_files,
    get_file_info,
    move_file,
    move_folder,
    copy_file,
    copy_folder,
    create_folder,
    delete_file,
    delete_folder,
    create_multiple_files,
)

# System command execution
from tools.system.system import execute_system_command

# Mouse and keyboard automation (expanded)
from tools.mouse_keyboard.automation import (
    move_mouse,
    click_mouse,
    double_click,
    drag_mouse,
    type_text,
    press_key,
    hotkey,
    screenshot,
    get_mouse_position,
    get_screen_size,
    scroll_mouse,
    move_and_click,
)

# Email tools (added list_email_folders)
from tools.email.email_tools import (
    search_emails,
    list_email_folders,
)

def get_all_tools():
    """
    Returns a list of all tool objects (professional versions).
    """
    return [
        # Math
        calculate,
        
        # File operations
        create_file,
        write_file,
        append_file,
        write_json,
        read_file,
        read_json,
        read_file_lines,
        list_folder_files,
        search_files,
        get_file_info,
        move_file,
        move_folder,
        copy_file,
        copy_folder,
        create_folder,
        delete_file,
        delete_folder,
        create_multiple_files,
        
        # System
        execute_system_command,
        
        # Mouse & Keyboard
        move_mouse,
        click_mouse,
        double_click,
        drag_mouse,
        type_text,
        press_key,
        hotkey,
        screenshot,
        get_mouse_position,
        get_screen_size,
        scroll_mouse,
        move_and_click,
        
        # Email
        search_emails,
        list_email_folders,
    ]