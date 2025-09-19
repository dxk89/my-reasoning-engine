import json

import pytest

from my_framework.apps import journalist


class DummyLLM:
    def __init__(self, *args, **kwargs):
        pass


@pytest.fixture
def patched_journalist(monkeypatch):
    monkeypatch.setattr(journalist, "scrape_content", lambda url: "scraped content")
    monkeypatch.setattr(
        journalist,
        "get_initial_draft",
        lambda llm, user_prompt, source_content: "draft",
    )
    monkeypatch.setattr(
        journalist,
        "get_revised_article",
        lambda llm, source_content, draft_article: "revised",
    )
    monkeypatch.setattr(journalist, "ChatOpenAI", DummyLLM)
    yield


def test_generate_article_normalizes_json(monkeypatch, patched_journalist):
    payload = {
        "title": "Test Title",
        "body": "<p>Body</p>",
        "seo_description": "Description",
        "seo_keywords": "key1, key2",
        "hashtags": ["#tag"],
    }
    fenced_json = f"```json\n{json.dumps(payload)}\n```"

    monkeypatch.setattr(
        journalist,
        "get_seo_metadata",
        lambda llm, revised_article: fenced_json,
    )

    result = journalist.generate_article_and_metadata.run(
        "https://example.com/article",
        "Write about testing",
        "gpt-test",
        "fake-key",
    )

    assert json.loads(result) == payload