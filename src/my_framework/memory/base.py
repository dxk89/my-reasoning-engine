# File: src/my_framework/memory/base.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any

from ..core.schemas import MessageType

class BaseMemory(ABC):
    """
    Abstract base class for memory. It defines the standard interface for how
    a chain interacts with memory.
    """
    
    # The key for the chat history list in the memory variables dictionary.
    # This is what the MessagesPlaceholder will look for.
    memory_key: str = "history"

    @abstractmethod
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, List[MessageType]]:
        """
        Loads the conversation history and returns it in a dictionary.
        This is called by the chain before formatting the prompt.
        """
        pass

    @abstractmethod
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """
        Saves the latest turn of the conversation to the memory store.
        This is called by the chain after the LLM has generated a response.
        """
        pass

    def clear(self) -> None:
        """A helper method to clear the memory."""
        pass