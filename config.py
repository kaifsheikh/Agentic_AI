# """
# Central configuration for the Agentic AI project.

# Loaded once here (from environment variables / .env) and imported by
# app.py, main.py, and agent_factory.py — so there's a single source of
# truth instead of each entry point reading os.getenv() separately.
# """
# import os
# from dotenv import load_dotenv

# # Load environment variables from .env as soon as this module is imported.
# load_dotenv()


# class Config:
#     DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
#     HOST = os.getenv("FLASK_HOST", "127.0.0.1")
#     PORT = int(os.getenv("FLASK_PORT", "5000"))
#     SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-me")

#     # LLM
#     GROQ_API_KEY = os.getenv("GROQ_API_KEY")
#     GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
#     TEMPERATURE = float(os.getenv("TEMPERATURE", "0"))

#     LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

#     # Paths
#     LOG_DIR = os.path.join(os.getcwd(), "logs")
#     LOG_FILE = os.path.join(LOG_DIR, "agentic_ai.log")

#     # CORS (optional)
#     CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")  # change in production

#     # Ensure log directory exists
#     os.makedirs(LOG_DIR, exist_ok=True)

#     # Validate API key
#     if not GROQ_API_KEY:
#         raise ValueError("GROQ_API_KEY environment variable not set. Please check .env file.")


"""
Central configuration. Sirf yahan env variables padho.
Baaki code Config.X use kare, os.getenv() direct kahin nahi.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    HOST = os.getenv("FLASK_HOST", "127.0.0.1")
    PORT = int(os.getenv("FLASK_PORT", "5000"))
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-me")

    # ============================================================
    # LLM Provider Selection
    # ============================================================
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "cloudflare").lower()
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0"))

    # ----- Groq -----
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    # ----- Cloudflare Workers AI -----
    CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
    CF_API_TOKEN = os.getenv("CF_API_TOKEN")
    CF_MODEL = os.getenv("CF_MODEL", "@cf/meta/llama-3.3-70b-instruct-fp8-fast")

    # ----- Google Gemini -----
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # ----- OpenAI (agar future mein chahiye) -----
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_DIR = os.path.join(os.getcwd(), "logs")
    LOG_FILE = os.path.join(LOG_DIR, "agentic_ai.log")
    os.makedirs(LOG_DIR, exist_ok=True)

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    # ============================================================
    # Validation — sirf selected provider ke keys check karo
    # ============================================================
    @classmethod
    def validate(cls):
        provider = cls.LLM_PROVIDER
        if provider == "groq" and not cls.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY missing in .env")
        if provider == "cloudflare" and (not cls.CF_ACCOUNT_ID or not cls.CF_API_TOKEN):
            raise ValueError("CF_ACCOUNT_ID / CF_API_TOKEN missing in .env")
        if provider == "gemini" and not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY missing in .env")
        if provider == "openai" and not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY missing in .env")
        if provider not in ("groq", "cloudflare", "gemini", "openai"):
            raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


Config.validate()