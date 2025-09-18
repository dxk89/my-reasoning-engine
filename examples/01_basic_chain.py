# File: examples/01_basic_chain.py

# CORRECTED IMPORT
from my_framework.models.openai import ChatOpenAI
from my_framework.prompts.templates import ChatPromptTemplate
from my_framework.parsers.standard import StrOutputParser
from my_framework.core.schemas import SystemMessage, HumanMessage

def main():
    """Demonstrates a simple sequential chain."""
    
    print("--- Running Basic Chain Example ---")
    
    # 1. Define the components
    prompt_template = ChatPromptTemplate(
        messages=[
            SystemMessage(content="You are a helpful assistant that writes short, witty poems."),
            HumanMessage(content="Write a four-line poem about {topic}.")
        ]
    )
    
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
    
    parser = StrOutputParser()
    
    # 2. Create the chain by piping the components together
    chain = prompt_template | llm | parser
    
    # 3. Invoke the chain with an input dictionary
    topic = "the moon"
    print(f"Invoking chain with topic: '{topic}'")
    
    response = chain.invoke({"topic": topic})
    
    # 4. Print the result
    print("\n--- Chain Output ---")
    print(response)
    print("---------------------\n")

if __name__ == "__main__":
    main()