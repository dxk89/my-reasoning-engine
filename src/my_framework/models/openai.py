# File: src/my_framework/models/openai.py

import os
from openai import OpenAI
from typing import List
from pydantic import Field, SecretStr, BaseModel, ConfigDict
from dotenv import load_dotenv

from .base import BaseChatModel, BaseEmbedding
from ..core.schemas import AIMessage, MessageType

load_dotenv()

class ChatOpenAI(BaseModel, BaseChatModel):
    """A wrapper for the OpenAI Chat Completion API."""

    # All settings are now correctly combined into this single model_config.
    model_config = ConfigDict(
        protected_namespaces=(),
        arbitrary_types_allowed=True
    )

    model_name: str = Field(default="gpt-4o", alias="model")
    temperature: float = 0.7
    api_key: SecretStr = Field(default_factory=lambda: SecretStr(os.environ.get("OPENAI_API_KEY", "")))

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

class OpenAIEmbedding(BaseEmbedding):
    """A wrapper for the OpenAI Embedding API."""

    # The same fix is applied here.
    model_config = ConfigDict(
        protected_namespaces=(),
        arbitrary_types_allowed=True
    )

    model_name: str = Field(default="text-embedding-3-small", alias="model")
    api_key: SecretStr = Field(default_factory=lambda: SecretStr(os.environ.get("OPENAI_API_KEY", "")))

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