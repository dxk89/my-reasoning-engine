# File: src/my_framework/apps/journalist.py

import os
import json
import time
from datetime import datetime, timedelta
import pytz
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager

from my_framework.agents.tools import tool
from my_framework.models.openai import ChatOpenAI
from my_framework.core.schemas import HumanMessage

# This is a simple logger that forces output to appear immediately in Render's logs.
def log(message):
    print(f"   - {message}", flush=True)

# (Your large MAP dictionaries go here... they are omitted for brevity but should be included)
# PASTE YOUR PUBLICATION_MAP, COUNTRY_MAP, and INDUSTRY_MAP here

# --- PROMPTS and HELPER FUNCTIONS ---
# (Your get_entity_extraction_prompt, get_subjective_metadata_prompt, and Selenium helpers go here)
# ...

# ==============================================================================
# TOOL 1: GENERATE ARTICLE CONTENT AND METADATA (WITH DETAILED LOGGING)
# ==============================================================================
@tool
def generate_article_and_metadata(source_url: str, user_prompt: str, ai_model: str, api_key: str) -> str:
    log("🤖 TOOL 1: Starting multi-step article and metadata generation...")

    # --- Step 1: Scrape Content ---
    log(f"   -> Step 1.1: Scraping content from {source_url}...")
    try:
        response = requests.get(source_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=90)
        response.raise_for_status()
        log("   -> Step 1.2: Web page request successful.")
        soup = BeautifulSoup(response.text, 'html.parser')
        source_content = ' '.join(p.get_text() for p in soup.find_all('p'))
        log(f"   -> Step 1.3: Successfully scraped {len(source_content)} characters.")
    except Exception as e:
        log(f"   -> 🔥 Step 1 FAILED: URL scraping failed: {e}")
        return json.dumps({"error": f"URL scraping failed: {e}"})

    llm = ChatOpenAI(model_name="gpt-4o", temperature=0.5, api_key=api_key)

    # --- Step 2: Write Initial Draft ---
    log("   -> Step 2.1: Writing initial draft...")
    # ... (drafting_prompt logic) ...
    draft_response = llm.invoke([{"role": "user", "content": drafting_prompt}])
    draft_article = draft_response.content
    log("   -> Step 2.2: Initial draft complete.")

    # --- Step 3: Fact-Check and Revise ---
    log("   -> Step 3.1: Fact-checking and revising draft...")
    # ... (revision_prompt logic) ...
    revision_response_raw = llm.invoke([{"role": "user", "content": revision_prompt}])
    log("   -> Step 3.2: Revision response received from LLM.")
    try:
        clean_json_text = revision_response_raw.content.strip().replace("```json", "").replace("```", "").strip()
        final_article_data = json.loads(clean_json_text)
        log("   -> Step 3.3: Successfully parsed fact-checked article JSON.")
    except Exception as e:
        log(f"   -> 🔥 Step 3 FAILED: Could not parse JSON from revision response: {e}")
        return json.dumps({"error": f"Failed to parse fact-checked article JSON. Response: {revision_response_raw.content}"})

    # --- Step 4: Generate Smart Metadata ---
    log("   -> Step 4.1: Generating smart metadata...")
    # ... (metadata_prompt logic) ...
    try:
        # ... (API call logic for metadata) ...
        log("   -> Step 4.2: Successfully generated and parsed metadata JSON.")
    except Exception as e:
        log(f"   -> 🔥 Step 4 FAILED: AI metadata generation failed: {e}")
        return json.dumps({"error": f"Failed to generate metadata with AI: {e}"})

    # --- Step 5: Combine and Return ---
    log("   -> Step 5.1: Combining all data...")
    final_data = {
        "title_value": final_article_data.get("title", ""),
        "body_value": final_article_data.get("body", ""),
        **metadata
    }
    log("✅ TOOL 1: Finished successfully.")
    return json.dumps(final_data)

# ==============================================================================
# TOOL 2: POST ARTICLE TO THE CMS (WITH DETAILED LOGGING)
# ==============================================================================
@tool
def post_article_to_cms(article_json_string: str, login_url: str, username: str, password: str, add_article_url: str, save_button_id: str) -> str:
    log("🤖 TOOL 2: Starting CMS Posting...")
    article_content = json.loads(article_json_string)
    driver = None
    try:
        log("   -> Step 1.1: Setting up Chrome WebDriver...")
        chrome_options = webdriver.ChromeOptions()
        if os.environ.get('RENDER', False):
            log("   -> Step 1.2: Configuring for Production (Headless) mode.")
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(options=chrome_options)
        else:
            log("   -> Step 1.2: Configuring for Local (Visible) mode.")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        log("   -> Step 1.3: WebDriver setup complete.")

        driver.implicitly_wait(20) # Increased wait time

        log(f"   -> Step 2.1: Navigating to login URL: {login_url}")
        driver.get(login_url)
        # ... (rest of the Selenium logic with logs before each major action)
        log("   -> Step 2.2: Entering username...")
        driver.find_element(By.ID, "edit-name").send_keys(username)
        log("   -> Step 2.3: Entering password...")
        driver.find_element(By.ID, "edit-pass").send_keys(password)
        log("   -> Step 2.4: Clicking submit...")
        driver.find_element(By.ID, "edit-submit").click()
        time.sleep(5)
        log("   -> Step 2.5: Login successful.")

        # ... and so on for the rest of the steps.
        
        log("✅ TOOL 2: Finished successfully.")
        return "Article posted successfully."
    except Exception as e:
        log(f"   -> 🔥 TOOL 2 FAILED: A critical error occurred: {e}")
        # Consider taking a screenshot on error for debugging
        # driver.save_screenshot("render_error_screenshot.png")
        return f"Failed to post article to CMS. Error: {e}"
    finally:
        if driver:
            log("   -> Closing WebDriver.")
            driver.quit()