# File: examples/02_rag_chain.py

# CORRECTED IMPORTS
from my_framework.models.openai import ChatOpenAI, OpenAIEmbedding
from my_framework.prompts.templates import ChatPromptTemplate
from my_framework.parsers.standard import StrOutputParser
from my_framework.core.schemas import SystemMessage, HumanMessage
from my_framework.core.runnables import RunnablePassthrough
from my_framework.data_connection.loaders import FileLoader
from my_framework.data_connection.splitters import RecursiveCharacterTextSplitter
from my_framework.data_connection.vectorstores import FAISSVectorStore
from my_framework.retrievers.base import VectorStoreRetriever

def format_docs(docs):
    """Helper function to format retrieved documents into a single string."""
    return "\n\n".join(doc.page_content for doc in docs)

def main():
    """Demonstrates a Retrieval-Augmented Generation (RAG) chain."""
    
    print("--- Running RAG Chain Example ---")
    
    # 1. Setup the RAG Pipeline (Load, Split, Embed, Store)
    print("1. Setting up the RAG pipeline...")
    loader = FileLoader("examples/sample_data.txt")
    documents = loader.load()
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=20)
    chunks = splitter.split_documents(documents)
    
    embedding_model = OpenAIEmbedding()
    vector_store = FAISSVectorStore(embedding_model=embedding_model)
    vector_store.add_documents(chunks)
    
    retriever = VectorStoreRetriever(vectorstore=vector_store, k=2)
    print("RAG pipeline setup complete.")
    
    # 2. Define the RAG chain
    prompt_template = ChatPromptTemplate(
        messages=[
            SystemMessage(content="You are an assistant for question-answering tasks. "
                                  "Use the following retrieved context to answer the question. "
                                  "If you don't know the answer, just say that you don't know."),
            HumanMessage(content="Question: {question}\n\nContext:\n{context}")
        ]
    )
    
    llm = ChatOpenAI(model_name="gpt-3.5-turbo")
    
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt_template
        | llm
        | StrOutputParser()
    )
    
    # 3. Invoke the chain
    question = "When was the Eiffel Tower completed?"
    print(f"\n3. Invoking chain with question: '{question}'")
    
    response = rag_chain.invoke(question)
    
    # 4. Print the result
    print("\n--- RAG Chain Output ---")
    print(response)
    print("------------------------\n")

if __name__ == "__main__":
    main()