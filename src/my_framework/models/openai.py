# File: my_framework/src/my_framework/models/openai.py

import os
from openai import OpenAI
from typing import List
from pydantic import Field, SecretStr, BaseModel 
from dotenv import load_dotenv

from .base import BaseChatModel, BaseEmbedding
from ..core.schemas import AIMessage, MessageType

load_dotenv()

# This class is correct as is. BaseModel comes first.
class ChatOpenAI(BaseModel, BaseChatModel):
    """A wrapper for the OpenAI Chat Completion API."""
    
    model_name: str = Field(default="gpt-4o", alias="model")
    temperature: float = 0.7
    api_key: SecretStr = Field(default_factory=lambda: SecretStr(os.environ.get("OPENAI_API_KEY", "")))
    
    class Config:
        arbitrary_types_allowed = True

    def _create_client(self):
        return OpenAI(api_key=self.api_key.get_secret_value())

    def invoke(self, input: List[MessageType], config=None) -> AIMessage:
        client = self._create_client()
        messages = [msg.model_dump() for msg in input]
        response = client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature
        )
        content = response.choices[0].message.content
        return AIMessage(content=content or "")

# --- THE FIX IS ON THE LINE BELOW ---
# We remove the redundant 'BaseModel' from this line.
class OpenAIEmbedding(BaseEmbedding):
    """A wrapper for the OpenAI Embedding API."""

    model_name: str = Field(default="text-embedding-3-small", alias="model")
    api_key: SecretStr = Field(default_factory=lambda: SecretStr(os.environ.get("OPENAI_API_KEY", "")))
    
    class Config:
        arbitrary_types_allowed = True

    def _create_client(self):
        return OpenAI(api_key=self.api_key.get_secret_value())

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        client = self._create_client()
        response = client.embeddings.create(
            model=self.model_name,
            input=texts
        )
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]