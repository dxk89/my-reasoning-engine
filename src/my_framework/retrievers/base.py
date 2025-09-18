# File: src/my_framework/retrievers/base.py

from typing import List
from ..core.runnables import Runnable
from ..core.schemas import Document
from ..data_connection.vectorstores import VectorStore

class VectorStoreRetriever(Runnable[str, List[Document]]):
    """
    A Runnable that wraps a VectorStore to retrieve documents.
    This is the component that will be used in RAG chains.
    """
    vectorstore: VectorStore
    k: int = 4 # Number of documents to retrieve

    def invoke(self, input: str, config=None) -> List[Document]:
        """
        Takes a query string and returns a list of relevant documents.
        """
        return self.vectorstore.similarity_search(query=input, k=self.k)