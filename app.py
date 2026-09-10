import os
import json
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional
import uuid

from flask import Flask, request, jsonify, render_template, Response, stream_with_context
from flask_cors import CORS  # optional, install with: pip install flask-cors

from config import Config
from agent_factory import build_agent, get_system_info

# ============================================================
# Logging Setup
# ============================================================
def setup_logging(app: Flask) -> None:
    """Configure logging for the application."""
    log_level = getattr(logging, Config.LOG_LEVEL, logging.INFO)

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
# System Info + Agent (built once at startup, shared across requests)
# ============================================================
system_info = get_system_info()
llm, tools, agent_app = build_agent()

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
    Handle chat requests (non-streaming, returns the full final answer at once).
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

@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    """
    Handle chat requests with token-by-token streaming via Server-Sent Events.
    Expected JSON: {"message": "...", "thread_id": "optional"}

    Emits a sequence of:
      data: {"token": "..."}\\n\\n
    followed by a final:
      data: {"done": true, "thread_id": "..."}\\n\\n
    (or a {"error": "..."} event if something goes wrong mid-stream).
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "error": "Invalid JSON payload"}), 400

    user_message = data.get("message", "").strip()
    thread_id = validate_thread_id(data.get("thread_id"))

    if not user_message:
        return jsonify({"status": "error", "error": "Message cannot be empty"}), 400

    if len(user_message) > 5000:
        return jsonify({"status": "error", "error": "Message too long (max 5000 chars)"}), 400

    thread_config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [("user", user_message)]}

    def generate():
        app.logger.info(f"Streaming message for thread {thread_id}: {user_message[:100]}...")
        try:
            # stream_mode="messages" yields (message_chunk, metadata) pairs as the
            # underlying model generates tokens, across every node in the graph.
            for message_chunk, metadata in agent_app.stream(
                inputs, config=thread_config, stream_mode="messages"
            ):
                content = getattr(message_chunk, "content", "")
                # Skip chunks coming from the "tools" node (tool call/results) so
                # only the model's actual answer text is streamed to the user.
                if content and metadata.get("langgraph_node") != "tools":
                    yield f"data: {json.dumps({'token': content}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True, 'thread_id': thread_id})}\n\n"
        except Exception as e:
            app.logger.error(f"Error in /api/chat/stream: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': 'Internal server error'})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering if ever deployed behind it
        },
    )

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
        # threaded=True so a streaming response doesn't block other requests
        # (e.g. /api/health) while the dev server is in use.
        app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT, threaded=True)
