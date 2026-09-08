import os
import getpass
import platform
import uuid
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from tools import get_all_tools

# Load environment variables from .env file
load_dotenv()

# System info
username = getpass.getuser()
os_name = platform.system()
user_home = f"C:/Users/{username}" if os_name == "Windows" else f"/Users/{username}"

system_prompt = f"""
Tum ek autonomous Agentic AI ho jo user ke system par local execution kar raha hai.
System Information:
- OS: {os_name}
- Current Username: {username}
- User Home Directory: {user_home}
- Desktop Path: {user_home}/Desktop

Guidance:
1. Jab user Desktop, Documents, ya System Commands ki baat kare, toh auto-detected paths use karo.
2. Direct exact tool run karo, user se username ya full path mat poocho.
3. Concise aur clear jawab do.

Language Instructions:
- Hamesha Roman Urdu (Latin script) mein jawab do.
- Devanagari (Hindi) script use mat karo.
- Example: "Aapki file ban gayi hai" likho, "आपकी फाइल बन गई है" mat likho.

Email Reading Capability:
- Aap user ke email inbox se emails search kar sakte ho.
- Jab user kisi naam, subject, ya keyword se email dhoondhne ko kahe, to 'search_emails' tool use karo.
- Query ko natural language mein accept karo aur tool ko sahi query do.
- Sirf read kar sakte ho, send nahi.
"""

tools = get_all_tools()

# API key environment variable se lein
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY environment variable not set. Please check your .env file.")

llm = ChatGroq(
    api_key=groq_api_key,
    model="openai/gpt-oss-20b",
    temperature=0
)

memory = MemorySaver()

app = create_agent(
    llm,
    tools,
    system_prompt=system_prompt,
    checkpointer=memory
)

if __name__ == "__main__":
    print("--- LangGraph Agentic AI Terminal Ready ---")
    print("Roman Urdu mein jawab milega.")
    print("'clear' likhne se memory reset ho jayegi.")

    current_thread_id = "user-session-1"
    config = {"configurable": {"thread_id": current_thread_id}}

    while True:
        user_input = input("\nAapka Sawal: ")

        if user_input.lower().strip() in ["exit", "quit", "close"]:
            print("Agent band ho raha hai. Allah Hafiz!")
            break

        if user_input.lower().strip() == "clear":
            current_thread_id = str(uuid.uuid4())
            config = {"configurable": {"thread_id": current_thread_id}}
            print("Memory clear ho gayi. Naya session shuru ho gaya.")
            continue

        if user_input.strip() == "":
            continue

        inputs = {"messages": [("user", user_input)]}
        response = app.invoke(inputs, config=config)

        final_message = response["messages"][-1].content
        print(f"\n[Final Answer]: {final_message}")