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
