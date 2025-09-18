# File: src/my_framework/memory/types.py

from typing import List, Dict, Any

from .base import BaseMemory
from ..core.schemas import MessageType, HumanMessage, AIMessage, SystemMessage
from ..models.base import BaseChatModel

class ConversationBufferMemory(BaseMemory):
    """
    The simplest memory strategy. It stores the entire conversation history
    in a buffer.
    
    Pros: Perfect recall, high-fidelity context[cite: 134].
    Cons: Can easily exceed the model's context window on long conversations[cite: 134].
    """
    chat_history: List[MessageType] = []

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, List[MessageType]]:
        return {self.memory_key: self.chat_history}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        # Assuming the primary input key is 'input' and output is 'output'
        user_input = next(iter(inputs.values()))
        ai_output = next(iter(outputs.values()))
        self.chat_history.append(HumanMessage(content=user_input))
        self.chat_history.append(AIMessage(content=ai_output))

    def clear(self) -> None:
        self.chat_history = []

class ConversationBufferWindowMemory(BaseMemory):
    """
    A more practical memory that keeps only the last 'k' interactions.
    
    Pros: Prevents context window overflow and has a predictable cost[cite: 136].
    Cons: Loses context from earlier in the conversation[cite: 136].
    """
    chat_history: List[MessageType] = []
    k: int = 5 # Number of conversational turns to keep (1 turn = 1 human + 1 AI message)

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, List[MessageType]]:
        # Return only the last k * 2 messages
        return {self.memory_key: self.chat_history[-(self.k * 2):]}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        user_input = next(iter(inputs.values()))
        ai_output = next(iter(outputs.values()))
        self.chat_history.append(HumanMessage(content=user_input))
        self.chat_history.append(AIMessage(content=ai_output))
        # Trim the history if it grows too long
        while len(self.chat_history) > self.k * 2:
            self.chat_history.pop(0)
    
    def clear(self) -> None:
        self.chat_history = []

class ConversationSummaryMemory(BaseMemory):
    """
    A long-term memory strategy that uses an LLM to create a running
    summary of the conversation.
    
    Pros: Can handle very long conversations within a small token footprint[cite: 139].
    Cons: Incurs extra LLM costs for summarization and can lose details[cite: 140].
    """
    llm: BaseChatModel
    summary: str = ""

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, List[MessageType]]:
        # The "history" is a single system message containing the summary
        return {self.memory_key: [SystemMessage(content=self.summary)]}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        user_input = next(iter(inputs.values()))
        ai_output = next(iter(outputs.values()))
        
        new_line = f"Human: {user_input}\nAI: {ai_output}"
        
        # Create a prompt to ask the LLM to update the summary
        prompt = [
            SystemMessage(content="You are a helpful AI that summarizes conversations."),
            HumanMessage(
                content=f"Please create a concise summary of the following conversation, "
                        f"incorporating the new lines into the existing summary.\n\n"
                        f"Current Summary:\n{self.summary}\n\n"
                        f"New Lines:\n{new_line}"
            )
        ]
        
        # Call the LLM to get the new summary
        response = self.llm.invoke(prompt)
        self.summary = response.content

    def clear(self) -> None:
        self.summary = ""