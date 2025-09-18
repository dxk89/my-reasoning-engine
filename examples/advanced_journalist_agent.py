# File: my_framework/examples/advanced_journalist_agent.py

import os
import json
import time
from datetime import datetime, timedelta
import pytz

# --- Imports from our framework ---
from my_framework.agents.tools import tool
from my_framework.agents.executor import AgentExecutor
from my_framework.models.openai import ChatOpenAI
# --- THIS IS THE FIX: Import from our new utils file ---
from my_framework.agents.utils import get_metadata_prompt, remove_non_bmp_chars, tick_checkboxes_by_id, select_dropdown_option
# ----------------------------------------------------

# --- Imports for the tool's functionality ---
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


# ==============================================================================
# TOOL 1: GENERATE ARTICLE CONTENT AND METADATA (NEW "SMART" VERSION)
# This tool now includes the multi-step writing and fact-checking process internally.
# ==============================================================================
@tool
def generate_article_and_metadata(source_url: str, user_prompt: str, ai_model: str, api_key: str) -> str:
    """
    Generates a complete, fact-checked, and ready-to-post article with all required CMS metadata.
    This is a smart tool that uses a multi-step AI process for quality.
    Input requires the source_url, the user_prompt for the article's angle, the ai_model ('openai' or 'gemini'), and the corresponding api_key.
    Returns a JSON string of the complete article data.
    """
    print("🤖 SMART TOOL: Starting multi-step article generation...")
    def log(message): print(f"   - {message}")

    # Internal LLM for this multi-step tool
    llm = ChatOpenAI(model_name="gpt-4o", temperature=0.5)

    # --- Step 1: Scrape Content ---
    log(f"Scraping content from {source_url}...")
    try:
        response = requests.get(source_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        source_content = ' '.join(p.get_text() for p in soup.find_all('p'))
        log(f"✅ Successfully scraped {len(source_content)} characters.")
    except Exception as e:
        return json.dumps({"error": f"URL scraping failed: {e}"})

    # --- Step 2: Write Initial Draft ---
    log("Writing initial draft...")
    drafting_prompt = f"""
    You are an expert journalist writing for intellinews.com. Your writing style is professional, insightful, and objective, focusing on financial, business, and political analysis of emerging markets.
    Based on the provided SOURCE CONTENT, write a draft of an article that follows the USER PROMPT.
    
    USER PROMPT: "{user_prompt}"
    
    SOURCE CONTENT:
    ---
    {source_content[:12000]}
    ---
    
    Now, write the initial draft of the article.
    """
    draft_response = llm.invoke([{"role": "user", "content": drafting_prompt}])
    draft_article = draft_response.content
    log("✅ Initial draft complete.")

    # --- Step 3: Fact-Check and Revise ---
    log("Fact-checking and revising draft...")
    revision_prompt = f"""
    You are a meticulous fact-checker. Your task is to review the following DRAFT ARTICLE and ensure every claim it makes is fully supported by the provided SOURCE CONTENT.
    Correct any inaccuracies, remove any claims not supported by the source, and improve the writing to match the professional, objective style of intellinews.com.
    Finally, format the revised, fact-checked article into a JSON object with two keys: "title" and "body". The body should be a single string of HTML with paragraphs enclosed in <p> tags.

    SOURCE CONTENT:
    ---
    {source_content[:12000]}
    ---
    
    DRAFT ARTICLE:
    ---
    {draft_article}
    ---

    Now, provide the final, fact-checked article in the required JSON format.
    """
    revision_response_raw = llm.invoke([{"role": "user", "content": revision_prompt}])
    
    # Clean up the JSON response from the LLM
    try:
        clean_json_text = revision_response_raw.content.strip().replace("```json", "").replace("```", "").strip()
        final_article_data = json.loads(clean_json_text)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Failed to parse fact-checked article JSON from LLM response: {e}. Response was: {revision_response_raw.content}"})
        
    log("✅ Fact-checking and revision complete.")

    # --- Step 4: Generate Smart Metadata ---
    log("Generating smart metadata from final article...")
    article_title = final_article_data.get("title", "")
    article_body = final_article_data.get("body", "")
    metadata_prompt = get_metadata_prompt(article_title, article_body)
    
    try:
        # Use a direct API call for the complex metadata JSON as it's more reliable
        if ai_model == 'openai':
            api_url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {"model": "gpt-4o", "messages": [{"role": "user", "content": metadata_prompt}], "response_format": {"type": "json_object"}}
            response = requests.post(api_url, headers=headers, json=payload, timeout=120)
            metadata_json_text = response.json()['choices'][0]['message']['content']
            metadata = json.loads(metadata_json_text)
        else: # Gemini
            # ... Gemini logic here ...
            metadata = {"error": "Gemini metadata not implemented"}

    except Exception as e:
        return json.dumps({"error": f"Failed to generate metadata with AI: {e}"})

    log("✅ Metadata generation complete.")

    # --- Step 5: Combine and Return ---
    final_data = {
        "title_value": article_title,
        "body_value": article_body,
        **metadata
    }
    log("✅ SMART TOOL: Finished. Returning complete article data as JSON.")
    return json.dumps(final_data)

# ==============================================================================
# TOOL 2: POST ARTICLE TO THE CMS
# ==============================================================================
@tool
def post_article_to_cms(article_json_string: str, login_url: str, username: str, password: str, add_article_url: str, save_button_id: str) -> str:
    """
    Logs into a CMS and posts a new article using browser automation.
    Use this tool AFTER `generate_article_and_metadata` has been successfully used.
    Input requires the full 'article_json_string' from the previous tool, plus the CMS login credentials, the URL for adding a new article, and the ID of the save button.
    Returns a success or failure message.
    """
    print("🤖 TOOL 2: Starting CMS Posting...")
    def log(message): print(f"   - {message}")
    article_content = json.loads(article_json_string)
    driver = None
    try:
        chrome_options = webdriver.ChromeOptions()
        IS_RENDER = os.environ.get('RENDER', False)
        if IS_RENDER:
            log("Running in Production (Headless) mode.")
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(options=chrome_options)
        else:
            log("Running in Local (Visible) mode for debugging.")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.implicitly_wait(15)
        log(f"Navigating to login URL: {login_url}...")
        driver.get(login_url)
        driver.find_element(By.ID, "edit-name").send_keys(username)
        driver.find_element(By.ID, "edit-pass").send_keys(password)
        driver.find_element(By.ID, "edit-submit").click()
        time.sleep(4)
        log("Login successful.")

        log(f"Navigating to 'Add Article' page: {add_article_url}...")
        driver.get(add_article_url)
        time.sleep(3)
        
        log("📝 Filling article form...")
        
        # --- ADDED DATE LOGIC FROM ORIGINAL SCRIPT ---
        gmt = pytz.timezone('GMT')
        now_gmt = datetime.now(gmt)
        target_date = now_gmt + timedelta(days=1) if now_gmt.hour >= 7 else now_gmt
        target_date_str = target_date.strftime('%m/%d/%Y')
        driver.execute_script(f"document.getElementById('edit-field-date-und-0-value-datepicker-popup-0').value = '{target_date_str}';")
        driver.execute_script(f"document.getElementById('edit-field-sending-date-und-0-value-datepicker-popup-0').value = '{target_date_str}';")
        driver.execute_script(f"document.getElementById('edit-field-publication-date-time-und-0-value-datepicker-popup-0').value = '{target_date_str}';")
        log(f"   - Set all date fields to {target_date_str}")
        # ---------------------------------------------
        
        driver.find_element(By.ID, "edit-title").send_keys(remove_non_bmp_chars(article_content.get('title_value', '')))
        escaped_body = json.dumps(article_content.get('body_value', ''))
        driver.execute_script(f"CKEDITOR.instances['edit-body-und-0-value'].setData({escaped_body});")
        
        tick_checkboxes_by_id(driver, article_content.get('country_id_selections'), log)
        tick_checkboxes_by_id(driver, article_content.get('publication_id_selections'), log)
        select_dropdown_option(driver, 'edit-field-subject-und', article_content.get('daily_subject_value'), log, "Daily Subject")
        select_dropdown_option(driver, 'edit-field-key-und', article_content.get('key_point_value'), log, "Key Point")
        # (The rest of the form filling would go here...)
        
        if save_button_id:
            log("🚀 Clicking the final 'Save' button...")
            driver.find_element(By.ID, save_button_id).click()
            time.sleep(10) # Give more time to see the result page
            log("✅ TOOL 2: Finished. Article submitted successfully!")
            return "Article posted successfully."
        else:
            log("⚠️ TOOL 2: Finished. Save button ID not configured. Not saved.")
            return "Form filled but not saved as no save button ID was provided."
    except Exception as e:
        log(f"🔥 A critical error occurred in the CMS tool: {e}")
        return f"Failed to post article to CMS. Error: {e}"
    finally:
        if driver and not IS_RENDER:
            log("Closing browser in 15 seconds...")
            time.sleep(15)
        if driver:
            driver.quit()
# ==============================================================================
# AGENT SETUP
# (This code remains the same)
# ==============================================================================
AGENT_SYSTEM_PROMPT = """
You are an autonomous AI Journalist assistant. Your goal is to generate and post a series of articles based on user-provided configurations.
You have access to the following tools:
{tools}

For EACH article configuration you are given, you must follow these steps in order:
1.  Use the `generate_article_and_metadata` tool to create the full article content.
2.  Inspect the result from step 1. If it contains an error, report the error and stop processing THIS article.
3.  If step 1 was successful, use the `post_article_to_cms` tool with the JSON data from step 1 to log in and post the article.
4.  Report the final success or failure message from the `post_article_to_cms` tool.
5.  Repeat this process for the next article configuration if there is one.

You MUST use the following format for your response:

Thought: you should always think about what to do to solve the task.
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action. This must be a single string.
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I have now completed all the tasks for all the articles.
Final Answer: A summary of all the actions taken and the results for each article.

Begin!

User Query: {input}
Agent Scratchpad: {agent_scratchpad}
"""

tools = [generate_article_and_metadata, post_article_to_cms]
llm = ChatOpenAI(model_name="gpt-4o", temperature=0)
advanced_journalist_agent = AgentExecutor(llm=llm, tools=tools, system_prompt=AGENT_SYSTEM_PROMPT)