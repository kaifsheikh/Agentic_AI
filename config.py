"""
Central configuration for the Agentic AI project.

Loaded once here (from environment variables / .env) and imported by
app.py, main.py, and agent_factory.py — so there's a single source of
truth instead of each entry point reading os.getenv() separately.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env as soon as this module is imported.
load_dotenv()


class Config:
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    HOST = os.getenv("FLASK_HOST", "127.0.0.1")
    PORT = int(os.getenv("FLASK_PORT", "5000"))
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-me")

    # LLM
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
