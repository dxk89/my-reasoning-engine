# File: src/my_framework/models/openai.py

import os
from openai import OpenAI, Timeout
from typing import List
from pydantic import Field, SecretStr, BaseModel, ConfigDict
from dotenv import load_dotenv

from .base import BaseChatModel, BaseEmbedding
from ..core.schemas import AIMessage, MessageType

load_dotenv()

def log(message):
    print(f"   - [openai.py] {message}", flush=True)

class ChatOpenAI(BaseModel, BaseChatModel):
    """A wrapper for the OpenAI Chat Completion API."""
    model_config = ConfigDict(
        protected_namespaces=(),
        arbitrary_types_allowed=True
    )

    model_name: str = Field(default="gpt-4o", alias="model")
    temperature: float = 0.7
    api_key: SecretStr = Field(default_factory=lambda: SecretStr(os.environ.get("OPENAI_API_KEY", "")))

    def invoke(self, input: List[MessageType], config=None) -> AIMessage:
        # --- THIS IS THE FIX ---
        # The client is initialized here without the unsupported 'proxies' argument.
        client = OpenAI(api_key=self.api_key.get_secret_value(), timeout=Timeout(120.0))
        # --------------------
        
        messages = [msg.model_dump() for msg in input]
        
        log(f"Sending request to OpenAI model '{self.model_name}'...")
        try:
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature
            )
            log("Successfully received response from OpenAI.")
            content = response.choices[0].message.content
            return AIMessage(content=content or "")
        except Timeout:
            log("🔥 OpenAI API call timed out after 120 seconds.")
            return AIMessage(content='{"error": "AI model timed out"}')
        except Exception as e:
            log(f"🔥 An unexpected error occurred during the OpenAI API call: {e}")
            return AIMessage(content=f'{{"error": "An unexpected error occurred with the AI model: {e}"}}')

class OpenAIEmbedding(BaseEmbedding):
    """A wrapper for the OpenAI Embedding API."""
    model_config = ConfigDict(
        protected_namespaces=(),
        arbitrary_types_allowed=True
    )

    model_name: str = Field(default="text-embedding-3-small", alias="model")
    api_key: SecretStr = Field(default_factory=lambda: SecretStr(os.environ.get("OPENAI_API_KEY", "")))
    
    def _create_client(self):
        # Ensure the 'proxies' argument is also removed here if present.
        return OpenAI(api_key=self.api_key.get_secret_value(), timeout=Timeout(120.0))

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        client = self._create_client()
        response = client.embeddings.create(
            model=self.model_name,
            input=texts
        )
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]