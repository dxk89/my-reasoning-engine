# File: my_framework/examples/writer_agent.py

import json
from bs4 import BeautifulSoup
import requests

from my_framework.agents.tools import tool
from my_framework.agents.executor import AgentExecutor
from my_framework.models.openai import ChatOpenAI
from my_framework.agents.utils import get_metadata_prompt

# --- TOOLS FOR THE WRITER AGENT ---

@tool
def get_content_from_url(url: str) -> str:
    """
    Fetches and returns the text content from a given web page URL.
    This should be the first tool used to get the source material for the article.
    """
    print(f"🤖 WRITER AGENT TOOL: Scraping content from {url}...")
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        text = ' '.join(p.get_text() for p in soup.find_all('p'))
        print(f"   - ✅ Scraping successful.")
        return text[:12000] # Return a generous portion of the text
    except Exception as e:
        print(f"   - 🔥 Scraping failed: {e}")
        return f"Error: Could not retrieve content from the URL. {e}"

@tool
def generate_fact_checked_article(user_prompt: str, source_content: str) -> str:
    """
    Writes, fact-checks, and revises an article based on the user's prompt and the source content.
    This tool performs a multi-step process to ensure quality and accuracy.
    It returns a JSON object with 'title' and 'body' of the final, checked article.
    """
    print("🤖 WRITER AGENT TOOL: Starting fact-checked article generation...")
    
    # Internal LLM for this multi-step tool
    llm = ChatOpenAI(model_name="gpt-4o", temperature=0.5)

    # 1. Draft the article
    print("   - Step 1: Writing initial draft...")
    drafting_prompt = f"""
    You are an expert journalist writing for intellinews.com. Your writing style is professional, insightful, and objective, focusing on financial, business, and political analysis of emerging markets.
    Based on the provided source content, write a draft of an article that follows the user's specific prompt.
    
    USER PROMPT: "{user_prompt}"
    
    SOURCE CONTENT:
    ---
    {source_content}
    ---
    
    Please write the initial draft of the article.
    """
    draft_response = llm.invoke([{"role": "user", "content": drafting_prompt}])
    draft_article = draft_response.content
    print("   - ✅ Initial draft complete.")
    
    # 2. Fact-check and revise the draft
    print("   - Step 2: Fact-checking and revising draft...")
    revision_prompt = f"""
    You are a meticulous fact-checker. Your task is to review the following DRAFT ARTICLE and ensure every claim it makes is fully supported by the provided SOURCE CONTENT.
    Correct any inaccuracies, remove any claims not supported by the source, and improve the writing to match the professional, objective style of intellinews.com.
    Finally, format the revised, fact-checked article into a JSON object with two keys: "title" and "body". The body should be a single string of HTML with paragraphs enclosed in <p> tags.

    SOURCE CONTENT:
    ---
    {source_content}
    ---
    
    DRAFT ARTICLE:
    ---
    {draft_article}
    ---

    Now, provide the final, fact-checked article in the required JSON format.
    """
    revision_response = llm.invoke([{"role": "user", "content": revision_prompt}])
    final_article_json = revision_response.content
    print("   - ✅ Fact-checking and revision complete.")
    
    return final_article_json

@tool
def generate_metadata(article_title: str, article_body: str, ai_model: str, api_key: str) -> str:
    """
    Generates all the required CMS metadata for a finished article.
    This should be the LAST tool used, after the article has been written and fact-checked.
    The input is the final article title and body.
    It returns a JSON string of the complete metadata.
    """
    print("🤖 WRITER AGENT TOOL: Generating smart metadata...")

    # For this specific task, we'll still use the direct AI call with the huge prompt,
    # as it's highly specialized for this JSON structure.
    if ai_model == 'openai':
        api_url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        prompt = get_metadata_prompt(article_title, article_body)
        payload = {"model": "gpt-4o", "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}
        response = requests.post(api_url, headers=headers, json=payload, timeout=120)
        json_text = response.json()['choices'][0]['message']['content']
        print("   - ✅ Metadata generation complete.")
        return json_text
    else: # Add Gemini logic if needed
        # ... (Gemini call logic would go here)
        return '{"error": "Gemini metadata generation not implemented in this tool."}'

# --- AGENT SETUP ---

AGENT_SYSTEM_PROMPT = """
You are a "Writer Agent". Your goal is to create a complete, fact-checked article and all its metadata, ready for publishing.

You MUST follow this sequence of actions:
1. Use the `get_content_from_url` tool to get the source material.
2. Use the `generate_fact_checked_article` tool, providing it with the user's prompt and the source content from step 1.
3. Use the `generate_metadata` tool, providing it with the final title and body from step 2.
4. Once you have the final article content (from step 2) and the final metadata (from step 3), combine them into a single JSON object.
5. Provide this final, combined JSON object as your Final Answer.

You have access to the following tools:
{tools}

Use the following format for your response:

Thought: ...
Action: ...
Action Input: ...
Observation: ...

Begin!

User Query: {input}
Agent Scratchpad: {agent_scratchpad}
"""

tools = [get_content_from_url, generate_fact_checked_article, generate_metadata]
llm = ChatOpenAI(model_name="gpt-4o", temperature=0)
writer_agent = AgentExecutor(llm=llm, tools=tools, system_prompt=AGENT_SYSTEM_PROMPT)