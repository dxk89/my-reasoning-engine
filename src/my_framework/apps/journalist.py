# File: src/my_framework/apps/journalist.py

import json
from my_framework.models.openai import ChatOpenAI
from my_framework.agents.tools import tool
from .scraper import scrape_content
from .llm_calls import get_initial_draft, get_revised_article, get_seo_metadata

def log(message):
    print(f"   - {message}", flush=True)

@tool
def generate_article_and_metadata(source_url: str, user_prompt: str, ai_model: str, api_key: str) -> str:
    """
    Generates a complete, fact-checked, and SEO-optimized article with metadata.
    """
    log("🤖 TOOL 1: Starting multi-step article generation process...")

    source_content = scrape_content(source_url)
    if "error" in source_content:
        return source_content

    llm = ChatOpenAI(model_name="gpt-4o", temperature=0.5, api_key=api_key)

    draft_article = get_initial_draft(llm, user_prompt, source_content)
    if "error" in draft_article:
        return draft_article

    revised_article = get_revised_article(llm, source_content, draft_article)
    if "error" in revised_article:
        return revised_article

    final_json_string = get_seo_metadata(llm, revised_article)
    if "error" in final_json_string:
        return final_json_string

    log("✅ TOOL 1: Finished successfully.")
    return final_json_string

@tool
def post_article_to_cms(article_json_string: str, login_url: str, username: str, password: str, add_article_url: str, save_button_id: str) -> str:
    # This tool's implementation remains the same.
    # ... (Your existing post_article_to_cms code) ...
    return "Article posted successfully."