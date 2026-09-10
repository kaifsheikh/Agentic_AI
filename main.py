import uuid

from agent_factory import build_agent


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

        inputs = {"messages": [("user", user_input)]}
        response = agent_app.invoke(inputs, config=config)

        final_message = response["messages"][-1].content
        print(f"\n[Final Answer]: {final_message}")


if __name__ == "__main__":
    run_terminal()
