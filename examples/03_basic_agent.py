# File: examples/03_basic_agent.py

import random
# CORRECTED IMPORTS
from my_framework.agents.tools import tool
from my_framework.agents.executor import AgentExecutor
from my_framework.models.openai import ChatOpenAI

# 1. Define the tools
@tool
def get_current_weather(location: str) -> str:
    """Gets the current weather for a specified location."""
    if "boston" in location.lower():
        return f"The weather in Boston is currently {random.randint(5, 15)}°C and sunny."
    elif "paris" in location.lower():
        return f"The weather in Paris is currently {random.randint(10, 20)}°C with light clouds."
    else:
        return f"I'm sorry, I don't have weather information for {location}."

@tool
def search_web(query: str) -> str:
    """Searches the web for information about a given query."""
    if "llm" in query.lower():
        return "A Large Language Model (LLM) is a type of artificial intelligence model..."
    else:
        return f"Search results for '{query}' did not yield a clear answer."

def main():
    """Demonstrates a ReAct agent with tools."""
    
    print("--- Running Basic Agent Example ---")

    # 2. Instantiate the components
    tools = [get_current_weather, search_web]
    llm = ChatOpenAI(model_name="gpt-4o", temperature=0) 
    
    agent_executor = AgentExecutor(llm=llm, tools=tools)
    
    # 3. Invoke the agent
    query = "What is the weather like in Boston?"
    print(f"\nInvoking agent with query: '{query}'")
    
    response = agent_executor.invoke({"input": query})
    
    # 4. Print the result
    print("\n--- Agent Final Answer ---")
    print(response)
    print("--------------------------\n")

if __name__ == "__main__":
    main()