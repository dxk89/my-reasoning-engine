# File: src/my_framework/data_connection/vectorstores.py

from abc import ABC, abstractmethod
from typing import List, Tuple
import numpy as np

from ..core.schemas import Document
from ..models.base import BaseEmbedding

# A library for efficient vector similarity search
import faiss 

class VectorStore(ABC):
    """Abstract base class for a vector store."""

    @abstractmethod
    def add_documents(self, documents: List[Document]):
        """Add documents to the vector store."""
        pass

    @abstractmethod
    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """Find the k most similar documents to a query."""
        pass

class FAISSVectorStore(VectorStore):
    """A simple in-memory vector store using FAISS."""

    def __init__(self, embedding_model: BaseEmbedding):
        self.embedding_model = embedding_model
        self.index = None
        self.documents: List[Document] = []

    def add_documents(self, documents: List[Document]):
        """Embeds documents and adds them to the FAISS index."""
        if not documents:
            return
            
        self.documents.extend(documents)
        texts = [doc.page_content for doc in documents]
        embeddings = self.embedding_model.embed_documents(texts)
        vectors = np.array(embeddings, dtype=np.float32)

        if self.index is None:
            # Initialize the index if it's the first time
            dimension = vectors.shape[1]
            self.index = faiss.IndexFlatL2(dimension)

        self.index.add(vectors)

    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """Performs a similarity search for the query."""
        if self.index is None:
            return []

        query_embedding = self.embedding_model.embed_query(query)
        query_vector = np.array([query_embedding], dtype=np.float32)

        # The search returns distances and indices of the nearest vectors
        distances, indices = self.index.search(query_vector, k)

        # Retrieve the corresponding documents
        results = [self.documents[i] for i in indices[0] if i < len(self.documents)]
        return results