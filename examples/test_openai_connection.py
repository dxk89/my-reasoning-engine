# File: examples/test_openai_connection.py

import os
from dotenv import load_dotenv
from my_framework.models.openai import ChatOpenAI
from my_framework.core.schemas import HumanMessage

# Load environment variables for local testing. Render provides them in production.
load_dotenv()

def run_test():
    """
    A simple function to test the connection to the OpenAI API.
    """
    print("--- 🧪 Starting OpenAI Connection Test ---")

    # 1. Check if the API key is available
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("--- 🔥 FAILURE: OPENAI_API_KEY environment variable not set. ---")
        return

    print("   - API key found. Initializing ChatOpenAI client...")

    try:
        # 2. Initialize the client (using the robust version from our last attempt)
        llm = ChatOpenAI(model_name="gpt-3.5-turbo")

        print("   - Client initialized successfully.")
        print("   - Sending a simple test message to the API...")

        # 3. Make the simplest possible API call
        response = llm.invoke([
            HumanMessage(content="Hello!")
        ])

        print(f"   - Received response from API: '{response.content}'")
        print("\n--- ✅ SUCCESS: The connection to the OpenAI API is working. ---")

    except Exception as e:
        print("\n--- 🔥 FAILURE: An error occurred while trying to connect to the OpenAI API. ---")
        print(f"   - Error Type: {type(e).__name__}")
        print(f"   - Error Details: {e}")
        print("------------------------------------------------------------------")

if __name__ == "__main__":
    run_test()