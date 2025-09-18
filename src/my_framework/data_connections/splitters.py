# File: src/my_framework/data_connection/splitters.py

from typing import List
from ..core.schemas import Document

class RecursiveCharacterTextSplitter:
    """
    Splits text recursively based on a list of separators.
    This tries to keep paragraphs, sentences, and words together as long as possible.
    """
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: List[str] | None = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", " ", ""]

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Splits a list of documents into smaller chunks."""
        all_chunks = []
        for doc in documents:
            chunks = self.split_text(doc.page_content)
            for chunk in chunks:
                all_chunks.append(
                    Document(page_content=chunk, metadata=doc.metadata.copy())
                )
        return all_chunks

    def split_text(self, text: str) -> List[str]:
        """The core recursive splitting logic."""
        final_chunks = []
        
        # Start with the largest separator
        separator = self.separators[0]
        splits = text.split(separator)
        
        good_splits = []
        # Merge splits that are too small
        for s in splits:
            if len(s) < self.chunk_size:
                good_splits.append(s)
            else:
                if good_splits:
                    merged = self._merge_splits(good_splits, separator)
                    final_chunks.extend(merged)
                    good_splits = []
                
                # If a split is still too big, recurse
                other_chunks = self.split_text_with_separators(s, self.separators[1:])
                final_chunks.extend(other_chunks)
        
        if good_splits:
            merged = self._merge_splits(good_splits, separator)
            final_chunks.extend(merged)
            
        return final_chunks

    def split_text_with_separators(self, text: str, separators: List[str]) -> List[str]:
        # A simplified helper for recursion
        if not separators or len(text) <= self.chunk_size:
            return [text] if text else []

        separator = separators[0]
        chunks = []
        for chunk in text.split(separator):
            if len(chunk) > self.chunk_size:
                chunks.extend(self.split_text_with_separators(chunk, separators[1:]))
            elif chunk:
                chunks.append(chunk)
        return chunks


    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        """Merges small splits into chunks of the desired size."""
        docs = []
        current_doc = ""
        for s in splits:
            if len(current_doc) + len(s) + len(separator) > self.chunk_size:
                if current_doc:
                    docs.append(current_doc)
                current_doc = s
            else:
                if current_doc:
                    current_doc += separator + s
                else:
                    current_doc = s
        if current_doc:
            docs.append(current_doc)
        return docs