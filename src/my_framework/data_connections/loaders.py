# File: src/my_framework/data_connection/loaders.py

from abc import ABC, abstractmethod
from typing import List

from ..core.schemas import Document

class BaseLoader(ABC):
    """Abstract base class for loading documents."""
    
    @abstractmethod
    def load(self) -> List[Document]:
        """Load documents from a source."""
        pass

class FileLoader(BaseLoader):
    """A simple loader for plain text files."""
    
    def __init__(self, file_path: str, encoding: str = "utf-8"):
        self.file_path = file_path
        self.encoding = encoding
        
    def load(self) -> List[Document]:
        """Loads a text file into a single Document."""
        try:
            with open(self.file_path, "r", encoding=self.encoding) as f:
                text = f.read()
            metadata = {"source": self.file_path}
            return [Document(page_content=text, metadata=metadata)]
        except FileNotFoundError:
            return []
        except Exception as e:
            print(f"Error loading file {self.file_path}: {e}")
            return []