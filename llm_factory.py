"""
Provider-agnostic LLM factory.
Naya provider add karna ho toh sirf yahan ek elif block add karo.
Baaki poora code (agent_factory, app, main) kabhi nahi badlega.
"""
from typing import Any
from config import Config


def build_llm() -> Any:
    """
    Config.LLM_PROVIDER ke hisaab se sahi LangChain chat model return karta hai.
    Sab models LangChain ke BaseChatModel interface follow karte hain,
    isliye agent_factory ko farq nahi padta konsa provider hai.
    """
    provider = Config.LLM_PROVIDER

    # ---------------- GROQ ----------------
    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            api_key=Config.GROQ_API_KEY,
            model=Config.GROQ_MODEL,
            temperature=Config.TEMPERATURE,
        )

    # ---------------- CLOUDFLARE WORKERS AI ----------------
    if provider == "cloudflare":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            api_key=Config.CF_API_TOKEN,
            base_url=(
                f"https://api.cloudflare.com/client/v4/accounts/"
                f"{Config.CF_ACCOUNT_ID}/ai/v1"
            ),
            model=Config.CF_MODEL,
            temperature=Config.TEMPERATURE,
            timeout=120.0,       # <-- NAYA: 2 minute timeout
            max_retries=2,       # <-- NAYA: retry
        )

    # ---------------- GOOGLE GEMINI ----------------
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            google_api_key=Config.GEMINI_API_KEY,
            model=Config.GEMINI_MODEL,
            temperature=Config.TEMPERATURE,
        )

    # ---------------- OPENAI ----------------
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL,
            temperature=Config.TEMPERATURE,
        )

    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")

def get_active_model_name() -> str:
    """
    Health endpoint aur logging ke liye current active model ka naam return karta hai.
    Config.LLM_PROVIDER ke hisaab se sahi model name deta hai.
    """
    provider = Config.LLM_PROVIDER

    if provider == "groq":
        return Config.GROQ_MODEL
    if provider == "cloudflare":
        return Config.CF_MODEL
    if provider == "gemini":
        return Config.GEMINI_MODEL
    if provider == "openai":
        return Config.OPENAI_MODEL

    return "unknown"