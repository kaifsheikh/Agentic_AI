import logging
import uuid

from agent_factory import build_agent

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_terminal():
    print("--- LangGraph Agentic AI Terminal Ready ---")
    print("Roman Urdu mein jawab milega.")
    print("'clear' likhne se memory reset ho jayegi.")

    _, _, agent_app = build_agent()

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

        # FIX: previously there was no error handling here at all — any
        # exception from agent_app.invoke() (bad tool call, provider
        # timeout, etc.) would crash the whole terminal session.
        try:
            inputs = {"messages": [("user", user_input)]}
            response = agent_app.invoke(inputs, config=config)
            final_message = response["messages"][-1].content
            print(f"\n[Final Answer]: {final_message}")
        except Exception as e:
            logger.error(f"Error while processing input: {e}", exc_info=True)
            print(f"\n[Error]: Kuch galat ho gaya, dobara try karein. ({type(e).__name__})")


if __name__ == "__main__":
    run_terminal()
