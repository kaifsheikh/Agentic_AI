"""
Agent construction. Ab kisi specific provider ka import nahi,
sirf build_llm() call karta hai.
"""
import getpass
import platform
from typing import Dict, Optional, Tuple

from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from config import Config
from llm_factory import build_llm
from tools import get_all_tools


def get_system_info() -> Dict[str, str]:
    username = getpass.getuser()
    os_name = platform.system()
    user_home = f"C:/Users/{username}" if os_name == "Windows" else f"/Users/{username}"
    return {
        "os": os_name,
        "username": username,
        "home": user_home,
        "desktop": f"{user_home}/Desktop",
    }


def build_system_prompt(system_info: Optional[Dict[str, str]] = None) -> str:
    info = system_info or get_system_info()
    return f"""
Tum ek autonomous Agentic AI ho jo user ke system par local execution kar raha hai.

System Information:
- OS: {info['os']}
- Current Username: {info['username']}
- User Home Directory: {info['home']}
- Desktop Path: {info['desktop']}
- Agentic_ai Folder: {info['desktop']}/Agentic_ai

CRITICAL TOOL RULES:
1. Jab bhi kisi folder ki files list karni ho, hamesha poora path do.
2. Kabhi bhi tool ko bina required arguments ke call mat karo.
3. Agar user ne path nahi bataya, to Desktop ya Agentic_ai folder assume karo.
4. Har tool call ke baad result check karo, error aaye to user ko batao.

Language Instructions:
- Hamesha Roman Urdu (Latin script) mein jawab do.
- Devanagari (Hindi) script use mat karo.

Email Capability:
- Aap user ke emails search kar sakte ho 'search_emails' tool se.
"""


def build_agent(checkpointer=None) -> Tuple[object, list, object]:
    """
    Returns (llm, tools, compiled_agent).
    llm ka concrete type ab provider par depend karta hai,
    lekin code ko uski parwah nahi — sirf LangChain interface chahiye.
    """
    tools = get_all_tools()
    llm = build_llm()             # <-- sirf yahan se aata hai
    memory = checkpointer or MemorySaver()

    agent_app = create_agent(
        llm,
        tools,
        system_prompt=build_system_prompt(),
        checkpointer=memory,
    )
    return llm, tools, agent_app