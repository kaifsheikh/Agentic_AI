"""
Shared agent construction logic for the Agentic AI project.

Both the Flask web server (app.py) and the terminal client (main.py)
import from here, so the system prompt, tool loading, and LLM/agent
setup live in exactly one place instead of being duplicated.
"""
import getpass
import platform
from typing import Dict, Optional, Tuple

from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from config import Config
from tools import get_all_tools


def get_system_info() -> Dict[str, str]:
    """Detect basic OS/user info used to ground the agent's system prompt."""
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
    """Build the single canonical system prompt used by every entry point."""
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
   Example: list_folder_files(folder_path="Desktop/Agentic_ai")
2. Kabhi bhi tool ko bina required arguments ke call mat karo.
3. Agar user ne path nahi bataya, to Desktop ya Agentic_ai folder assume karo.
4. Har tool call ke baad result check karo, error aaye to user ko batao.

Language Instructions:
- Hamesha Roman Urdu (Latin script) mein jawab do.
- Devanagari (Hindi) script use mat karo.
- Example: "Aapki file ban gayi hai" likho, "आपकी फाइल बन गई है" mat likho.

Email Capability:
- Aap user ke emails search kar sakte ho 'search_emails' tool se.
- Query natural language mein accept karo aur tool ko sahi query do.
- Sirf read kar sakte ho, send nahi.
"""


def build_agent(checkpointer=None) -> Tuple[ChatGroq, list, object]:
    """
    Construct the (llm, tools, compiled agent) triple using shared config.

    checkpointer: optional custom LangGraph checkpointer (e.g. a Sqlite/Postgres
    saver for persistent memory). Defaults to an in-memory MemorySaver, which
    is lost on restart -- fine for local/dev use.
    """
    tools = get_all_tools()

    llm = ChatGroq(
        api_key=Config.GROQ_API_KEY,
        model=Config.GROQ_MODEL,
        temperature=Config.TEMPERATURE,
    )

    memory = checkpointer or MemorySaver()

    agent_app = create_agent(
        llm,
        tools,
        system_prompt=build_system_prompt(),
        checkpointer=memory,
    )

    return llm, tools, agent_app
