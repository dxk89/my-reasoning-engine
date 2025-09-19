import json
import textwrap
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI()

# JSON schema for the final article object
ARTICLE_JSON_SCHEMA = {
    "name": "article_schema",
    "schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "body": {"type": "string"},
            "seo_description": {"type": "string"},
            "seo_keywords": {
                "type": "array",
                "items": {"type": "string"}
            },
            "hashtags": {
                "type": "array",
                "items": {"type": "string"}
            },
            "meta": {
                "type": "object",
                "properties": {
                    "source_url": {"type": "string"},
                    "published_at": {"type": "string"},
                    "byline": {"type": "string"}
                },
                "additionalProperties": True
            }
        },
        "required": ["title", "body", "seo_description", "seo_keywords"],
        "additionalProperties": True
    }
}

# System message to force JSON output
SYSTEM_JSON_ONLY = textwrap.dedent("""
You are a formatter that outputs ONLY valid JSON that conforms to the provided schema.
- No code fences
- No prose
- No comments
- No emojis
- No trailing commas
""").strip()


# ---- JSON Helper Functions ---- #

def extract_first_json_block(text: str) -> str | None:
    """
    Finds the first balanced {...} JSON object in text.
    Returns the substring or None if not found.
    """
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    return None


def safe_load_json(maybe_json: str):
    """
    Safely loads JSON, even if the AI response has stray text.
    """
    # Try direct parse
    try:
        return json.loads(maybe_json)
    except Exception:
        pass

    # Try extracting first {...} block
    block = extract_first_json_block(maybe_json)
    if not block:
        raise ValueError("No JSON object found in model output.")

    # Clean up weird quotes or backticks
    cleaned = (
        block.replace("“", "\"")
             .replace("”", "\"")
             .replace("’", "'")
             .replace("`", "")
    )
    return json.loads(cleaned)


def normalize_article(doc: dict) -> dict:
    """
    Normalizes metadata fields into lists.
    """
    if isinstance(doc.get("seo_keywords"), str):
        doc["seo_keywords"] = [s.strip() for s in doc["seo_keywords"].split(",") if s.strip()]
    if isinstance(doc.get("hashtags"), str):
        doc["hashtags"] = [s.strip() for s in doc["hashtags"].split(",") if s.strip()]
    return doc


# ---- Main LLM Call ---- #

def call_model_for_article_json(messages):
    """
    Calls the LLM and enforces JSON-only output.
    """
    resp = client.responses.create(
        model="gpt-4o",
        messages=messages + [{"role": "system", "content": SYSTEM_JSON_ONLY}],
        response_format={"type": "json_schema", "json_schema": ARTICLE_JSON_SCHEMA},
        max_output_tokens=2000,
        temperature=0.2,
        timeout_ms=60000  # 60 seconds instead of 20
    )

    # Get raw output text
    raw_text = resp.output_text

    # Save to file for debugging
    with open("/tmp/final_output.txt", "w", encoding="utf-8") as f:
        f.write(raw_text)

    # Parse + normalize
    parsed = safe_load_json(raw_text)
    parsed = normalize_article(parsed)
    return parsed


# ---- ChatOpenAI Wrapper Class ---- #

class ChatOpenAI:
    """
    A lightweight wrapper around OpenAI’s chat completions API. Instances of this
    class can be used anywhere in the framework where a ChatOpenAI with an
    `.invoke()` method is expected.
    """
    def __init__(
        self,
        model_name: str = "gpt-3.5-turbo",
        temperature: float = 0.5,
        api_key: str | None = None,
        max_tokens: int = 2000
    ) -> None:
        # Allow per-instance API key override; falls back to env if None
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

    def invoke(self, messages):
        """
        Send a list of messages to the chat model and return a simple object
        with a `.content` attribute containing the assistant’s reply.
        Each message should be either a dict with 'role' and 'content' fields,
        or an instance of my_framework.core.schemas.BaseMessage (which has
        .role and .content attributes).
        """
        formatted = []
        for m in messages:
            # Convert pydantic messages or dicts to the format expected by the API
            if hasattr(m, "role") and hasattr(m, "content"):
                formatted.append({"role": m.role, "content": m.content})
            elif isinstance(m, dict) and "role" in m and "content" in m:
                formatted.append({"role": m["role"], "content": m["content"]})
            else:
                raise ValueError(f"Unsupported message type: {m!r}")

            # The OpenAI API currently only supports the three roles "system", "user"
            # (for human messages) and "assistant" (for AI messages). If the caller
            # passes something different, it may cause an API error. We do not
            # enforce role validation here to preserve backwards compatibility.

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=formatted,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        # Wrap the content in a simple object that exposes a `.content` property,
        # similar to the return type used by other parts of the framework.
        class _Result:
            def __init__(self, content):
                self.content = content

        return _Result(response.choices[0].message.content)
