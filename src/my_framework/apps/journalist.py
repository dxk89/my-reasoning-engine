# File: src/my_framework/apps/journalist.py

import os
import json
import time
import requests
from bs4 import BeautifulSoup

from my_framework.models.openai import ChatOpenAI
from my_framework.core.schemas import HumanMessage, SystemMessage
from my_framework.agents.tools import tool

# Centralized logger for immediate output on Render
def log(message):
    print(f"   - {message}", flush=True)

# ==============================================================================
# TOOL 1: GENERATE ARTICLE AND METADATA
# ==============================================================================
@tool
def generate_article_and_metadata(source_url: str, user_prompt: str, ai_model: str, api_key: str) -> str:
    """
    Generates a complete, fact-checked, and SEO-optimized article with metadata.
    """
    log("🤖 TOOL 1: Starting multi-step article generation process...")

    # --- Step A: Scrape Content ---
    log(f"   -> Step A.1: Scraping content from {source_url}...")
    try:
        response = requests.get(source_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=90)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p', limit=40) # Increased paragraph limit slightly
        source_content = ' '.join(p.get_text() for p in paragraphs)
        log(f"   -> Step A.2: Scraping successful ({len(source_content)} characters).")
    except Exception as e:
        log(f"   -> 🔥 Step A FAILED: URL scraping failed: {e}")
        return json.dumps({"error": f"URL scraping failed: {e}"})

    # Initialize the LLM client once
    llm = ChatOpenAI(model_name="gpt-4o", temperature=0.5, api_key=api_key)

    # --- Step 1: Initial Draft ---
    log("   -> Step 1.1: Building prompt for initial draft.")
    draft_prompt = [
        SystemMessage(content="You are an expert journalist. Your task is to write a professional, insightful, and objective article based on the user's prompt and the provided source content. Focus on financial, business, and political analysis of emerging markets."),
        HumanMessage(content=f"USER PROMPT: \"{user_prompt}\"\n\nSOURCE CONTENT:\n---\n{source_content}\n---\n\nWrite the initial draft of the article now.")
    ]
    log("   -> Step 1.2: Sending request to LLM for initial draft...")
    draft_response = llm.invoke(draft_prompt)
    if "error" in draft_response.content:
        log(f"   -> 🔥 Step 1 FAILED: LLM returned an error: {draft_response.content}")
        return draft_response.content
    draft_article = draft_response.content
    log(f"   -> Step 1.3: Initial draft received ({len(draft_article)} characters).")

    # --- Step 2 & 3: Fact-Check and Stylistic Improvement ---
    log("   -> Step 2.1: Building prompt for fact-checking and stylistic improvements.")
    revision_prompt = [
        SystemMessage(content="You are a meticulous editor for intellinews.com. Your task is to review a draft article. First, ensure every claim is fully supported by the provided SOURCE CONTENT, correcting any inaccuracies. Second, refine the writing to match the professional, insightful, and objective style of intellinews.com."),
        HumanMessage(content=f"SOURCE CONTENT:\n---\n{source_content}\n---\n\nDRAFT ARTICLE:\n---\n{draft_article}\n---\n\nPlease provide the revised, fact-checked, and stylistically improved article.")
    ]
    log("   -> Step 2.2: Sending request to LLM for revision...")
    revised_response = llm.invoke(revision_prompt)
    if "error" in revised_response.content:
        log(f"   -> 🔥 Step 2 FAILED: LLM returned an error: {revised_response.content}")
        return revised_response.content
    revised_article = revised_response.content
    log(f"   -> Step 2.3: Revised article received ({len(revised_article)} characters).")

    # --- Step 4: SEO Optimization and Final JSON Formatting ---
    log("   -> Step 3.1: Building prompt for SEO optimization and JSON formatting.")
    seo_prompt = [
        SystemMessage(content="You are an SEO expert and content strategist. Your task is to take a final article and prepare it for publishing by creating a title and all necessary SEO metadata. Format the entire output as a single, valid JSON object."),
        HumanMessage(content=f"""
        Based on the following article, please perform these tasks:
        1. Create a concise, compelling, SEO-friendly title.
        2. Create a concise, engaging SEO meta description (155 characters max).
        3. Generate a list of relevant SEO keywords as a comma-separated string.
        4. Generate a list of 3-5 relevant social media hashtags (e.g., ["#Slovenia", "#Aviation"]).

        ARTICLE:
        ---
        {revised_article}
        ---

        Return a single JSON object with the following keys: "title" (string), "body" (string, which is the full revised article HTML-formatted with <p> tags), "seo_description" (string), "seo_keywords" (string), and "hashtags" (array of strings).
        """)
    ]
    log("   -> Step 3.2: Sending request to LLM for final SEO and formatting...")
    final_response = llm.invoke(seo_prompt)
    if "error" in final_response.content:
        log(f"   -> 🔥 Step 3 FAILED: LLM returned an error: {final_response.content}")
        return final_response.content
    final_json_string = final_response.content
    log("   -> Step 3.3: Final JSON object received.")

    log("✅ TOOL 1: Finished successfully.")
    return final_json_string


# ==============================================================================
# TOOL 2: POST ARTICLE TO THE CMS
# ==============================================================================
@tool
def post_article_to_cms(article_json_string: str, login_url: str, username: str, password: str, add_article_url: str, save_button_id: str) -> str:
    # This tool's implementation remains the same.
    # ... (Your existing post_article_to_cms code) ...
    return "Article posted successfully."