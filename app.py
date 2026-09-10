import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any
import uuid
import getpass
import platform

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS  # optional, install with: pip install flask-cors
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from tools import get_all_tools

# Load environment variables
load_dotenv()

# ============================================================
# Configuration
# ============================================================
class Config:
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    HOST = os.getenv("FLASK_HOST", "127.0.0.1")
    PORT = int(os.getenv("FLASK_PORT", "5000"))
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-me")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

    # Paths
    LOG_DIR = os.path.join(os.getcwd(), "logs")
    LOG_FILE = os.path.join(LOG_DIR, "agentic_ai.log")

    # CORS (optional)
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")  # change in production

    # Ensure log directory exists
    os.makedirs(LOG_DIR, exist_ok=True)

    # Validate API key
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY environment variable not set. Please check .env file.")

# ============================================================
# Logging Setup
# ============================================================
def setup_logging(app: Flask) -> None:
    """Configure logging for the application."""
    log_level = getattr(logging, Config.LOG_LEVEL, logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # File handler (rotating)
    file_handler = RotatingFileHandler(
        Config.LOG_FILE,
        maxBytes=10_000_000,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Werkzeug logger (Flask's built-in) also use our handlers
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.handlers = []
    werkzeug_logger.addHandler(file_handler)
    werkzeug_logger.addHandler(console_handler)
    werkzeug_logger.setLevel(log_level)
    
    app.logger.info("Logging configured.")

# ============================================================
# Initialize Flask App
# ============================================================
app = Flask(__name__)
app.config.from_object(Config)

# CORS (optional)
if Config.CORS_ORIGINS:
    CORS(app, resources={r"/api/*": {"origins": Config.CORS_ORIGINS}})

# Setup logging after app creation
setup_logging(app)
app.logger.info("Starting Agentic AI Web Server...")

# ============================================================
# System Information
# ============================================================
def get_system_info() -> Dict[str, str]:
    username = getpass.getuser()
    os_name = platform.system()
    if os_name == "Windows":
        user_home = f"C:/Users/{username}"
    else:
        user_home = f"/Users/{username}"
    return {
        "os": os_name,
        "username": username,
        "home": user_home,
        "desktop": os.path.join(user_home, "Desktop")
    }

system_info = get_system_info()

# ============================================================
# System Prompt
# ============================================================
system_prompt = f"""
Tum ek autonomous Agentic AI ho jo user ke system par local execution kar raha hai.

System Information:
- OS: {system_info['os']}
- Current Username: {system_info['username']}
- User Home Directory: {system_info['home']}
- Desktop Path: {system_info['desktop']}
- Agentic_ai Folder: {system_info['desktop']}/Agentic_ai

CRITICAL TOOL RULES:
1. Jab bhi kisi folder ki files list karni ho, hamesha poora path do.
   Example: list_folder_files(folder_path="Desktop/Agentic_ai")
2. Kabhi bhi tool ko bina required arguments ke call mat karo.
3. Agar user ne path nahi bataya, to Desktop ya Agentic_ai folder assume karo.
4. Har tool call ke baad result check karo, error aaye to user ko batao.

Language Instructions:
- Hamesha Roman Urdu (Latin script) mein jawab do.
- Devanagari (Hindi) script use mat karo.
- Example: "Aapki file ban gayi hai" likho.

Email Capability:
- Aap user ke emails search kar sakte ho 'search_emails' tool se.
- Query natural language mein accept karo.
- Sirf read kar sakte ho, send nahi.
"""

# ============================================================
# Load Tools and Initialize Agent
# ============================================================
tools = get_all_tools()

llm = ChatGroq(
    api_key=Config.GROQ_API_KEY,
    model=Config.GROQ_MODEL,
    temperature=Config.TEMPERATURE
)

memory = MemorySaver()

agent_app = create_agent(
    llm,
    tools,
    system_prompt=system_prompt,
    checkpointer=memory
)

app.logger.info(f"Agent initialized with {len(tools)} tools.")

# ============================================================
# Helper Functions
# ============================================================
def validate_thread_id(thread_id: Optional[str]) -> str:
    """Validate and sanitize thread_id."""
    if not thread_id or not isinstance(thread_id, str):
        return "user-session-default"
    # Limit length and remove any path separators to prevent injection
    thread_id = thread_id.strip()
    if len(thread_id) > 100:
        thread_id = thread_id[:100]
    # Replace any characters that could cause issues in file paths
    thread_id = "".join(c for c in thread_id if c.isalnum() or c in "-_")
    return thread_id

# ============================================================
# Routes
# ============================================================
@app.route("/")
def index():
    """Serve the frontend interface."""
    return render_template("index.html")

@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "model": Config.GROQ_MODEL,
        "os": system_info["os"],
        "tools_count": len(tools)
    })

@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Handle chat requests.
    Expected JSON: {"message": "...", "thread_id": "optional"}
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"status": "error", "error": "Invalid JSON payload"}), 400
        
        user_message = data.get("message", "").strip()
        thread_id = validate_thread_id(data.get("thread_id"))
        
        if not user_message:
            return jsonify({"status": "error", "error": "Message cannot be empty"}), 400
        
        if len(user_message) > 5000:
            return jsonify({"status": "error", "error": "Message too long (max 5000 chars)"}), 400
        
        config = {"configurable": {"thread_id": thread_id}}
        inputs = {"messages": [("user", user_message)]}
        
        app.logger.info(f"Processing message for thread {thread_id}: {user_message[:100]}...")
        response = agent_app.invoke(inputs, config=config)
        final_message = response["messages"][-1].content
        
        return jsonify({
            "status": "success",
            "response": final_message,
            "thread_id": thread_id
        })
    except Exception as e:
        app.logger.error(f"Error in /api/chat: {e}", exc_info=True)
        return jsonify({"status": "error", "error": "Internal server error"}), 500

@app.route("/api/clear", methods=["POST"])
def clear_session():
    """Clear the session by generating a new thread_id."""
    new_thread_id = str(uuid.uuid4())
    app.logger.info(f"Cleared session, new thread_id: {new_thread_id}")
    return jsonify({
        "status": "success",
        "message": "Session cleared",
        "thread_id": new_thread_id
    })

# ============================================================
# Error Handlers
# ============================================================
@app.errorhandler(404)
def not_found(e):
    return jsonify({"status": "error", "error": "Resource not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"status": "error", "error": "Internal server error"}), 500

# ============================================================
# Main Entry Point
# ============================================================
if __name__ == "__main__":
    app.logger.info(f"Starting Flask server on {Config.HOST}:{Config.PORT} (debug={Config.DEBUG})")
    # Use waitress for production (install: pip install waitress)
    if not Config.DEBUG and os.name != "nt":
        from waitress import serve
        serve(app, host=Config.HOST, port=Config.PORT)
    else:
        app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)