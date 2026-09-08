import os
import getpass
import platform
import uuid
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from tools import get_all_tools

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

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

groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY environment variable not set. Please check your .env file.")

llm = ChatGroq(
    api_key=groq_api_key,
    model="openai/gpt-oss-20b",
    temperature=0
)

memory = MemorySaver()

agent_app = create_agent(
    llm,
    tools,
    system_prompt=system_prompt,
    checkpointer=memory
)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()
    thread_id = data.get("thread_id", "user-session-1")

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [("user", user_message)]}

    try:
        response = agent_app.invoke(inputs, config=config)
        final_message = response["messages"][-1].content
        return jsonify({"response": final_message, "thread_id": thread_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/clear", methods=["POST"])
def clear_session():
    new_thread_id = str(uuid.uuid4())
    return jsonify({"message": "Session cleared", "thread_id": new_thread_id})

if __name__ == "__main__":
    print("--- Flask Agentic AI Web Server Starting ---")
    app.run(debug=True, port=5000, host="127.0.0.1")
