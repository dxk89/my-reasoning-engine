# File: src/my_framework/apps/llm_calls.py

from my_framework.models.openai import ChatOpenAI
from my_framework.core.schemas import SystemMessage, HumanMessage
import json

def log(message):
    print(f"   - {message}", flush=True)

def get_initial_draft(llm: ChatOpenAI, user_prompt: str, source_content: str) -> str:
    """
    Generates the initial draft of the article.
    """
    log("-> Building prompt for initial draft.")
    draft_prompt = [
        SystemMessage(content="You are an expert journalist. Your task is to write a professional, insightful, and objective article based on the user's prompt and the provided source content. Focus on financial, business, and political analysis of emerging markets."),
        HumanMessage(content=f"USER PROMPT: \"{user_prompt}\"\n\nSOURCE CONTENT:\n---\n{source_content}\n---\n\nWrite the initial draft of the article now.")
    ]
    log("-> Sending request to LLM for initial draft...")
    draft_response = llm.invoke(draft_prompt)
    if "error" in draft_response.content:
        log(f"-> 🔥 LLM returned an error: {draft_response.content}")
        return draft_response.content
    draft_article = draft_response.content
    log(f"-> Initial draft received ({len(draft_article)} characters).")
    return draft_article

def get_revised_article(llm: ChatOpenAI, source_content: str, draft_article: str) -> str:
    """
    Fact-checks and improves the style of the article.
    """
    log("-> Building prompt for fact-checking and stylistic improvements.")
    revision_prompt = [
        SystemMessage(content="You are a meticulous editor for intellinews.com. Your task is to review a draft article. First, ensure every claim is fully supported by the provided SOURCE CONTENT, correcting any inaccuracies. Second, refine the writing to match the professional, insightful, and objective style of intellinews.com."),
        HumanMessage(content=f"SOURCE CONTENT:\n---\n{source_content}\n---\n\nDRAFT ARTICLE:\n---\n{draft_article}\n---\n\nPlease provide the revised, fact-checked, and stylistically improved article.")
    ]
    log("-> Sending request to LLM for revision...")
    revised_response = llm.invoke(revision_prompt)
    if "error" in revised_response.content:
        log(f"-> 🔥 LLM returned an error: {revised_response.content}")
        return revised_response.content
    revised_article = revised_response.content
    log(f"-> Revised article received ({len(revised_article)} characters).")
    return revised_article

def get_seo_metadata(llm: ChatOpenAI, revised_article: str) -> str:
    """
    Generates SEO metadata and formats the final output.
    """
    log("-> Building prompt for SEO optimization and JSON formatting.")
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
    log("-> Sending request to LLM for final SEO and formatting...")
    final_response = llm.invoke(seo_prompt)
    if "error" in final_response.content:
        log(f"-> 🔥 LLM returned an error: {final_response.content}")
        return final_response.content
    final_json_string = final_response.content
    log("-> Final JSON object received.")
    return final_json_string