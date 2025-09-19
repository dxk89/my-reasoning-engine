import json
import os
import time
from datetime import datetime, timedelta

import pytz
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

from my_framework.agents.utils import (
    remove_non_bmp_chars,
    select_dropdown_option,
    tick_checkboxes_by_id,
)
from my_framework.models.openai import ChatOpenAI, safe_load_json, normalize_article
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
    if isinstance(source_content, dict) and "error" in source_content:
        return json.dumps(source_content)

    llm = ChatOpenAI(model_name="gpt-4o", temperature=0.5, api_key=api_key)

    draft_article = get_initial_draft(llm, user_prompt, source_content)
    if isinstance(draft_article, dict) and "error" in draft_article:
        return json.dumps(draft_article)

    revised_article = get_revised_article(llm, source_content, draft_article)
    if isinstance(revised_article, dict) and "error" in revised_article:
        return json.dumps(revised_article)

    final_json_string = get_seo_metadata(llm, revised_article)
    if isinstance(final_json_string, dict) and "error" in final_json_string:
        return json.dumps(final_json_string)

    try:
        parsed = safe_load_json(final_json_string)
        parsed = normalize_article(parsed)
        final_json_string = json.dumps(parsed)
    except Exception:
        pass

    log("✅ TOOL 1: Finished successfully.")
    return final_json_string


@tool
def post_article_to_cms(
    article_json_string: str,
    login_url: str,
    username: str,
    password: str,
    add_article_url: str,
    save_button_id: str,
) -> str:
    """
    Logs into the CMS and submits an article using browser automation.
    """
    log("🤖 TOOL 2: Starting CMS Posting...")
    
    try:
        article_content = json.loads(article_json_string)
        if "error" in article_content:
            return json.dumps(article_content)
    except (json.JSONDecodeError, TypeError) as e:
        return json.dumps({"error": f"Invalid JSON provided to post_article_to_cms: {e}"})

    driver = None
    try:
        # --- Simplified and Hardened Selenium Setup ---
        chrome_options = webdriver.ChromeOptions()
        
        binary_path = os.environ.get("GOOGLE_CHROME_BIN")
        driver_path = os.environ.get("CHROMEDRIVER_PATH")

        if not binary_path or not os.path.isfile(binary_path):
            error_msg = f"Chrome binary not found or is not a file. GOOGLE_CHROME_BIN='{binary_path}'"
            log(f"   - 🔥 {error_msg}")
            return json.dumps({"error": error_msg})
        
        if not driver_path or not os.path.isfile(driver_path):
            error_msg = f"ChromeDriver not found or is not a file. CHROMEDRIVER_PATH='{driver_path}'"
            log(f"   - 🔥 {error_msg}")
            return json.dumps({"error": error_msg})
        
        log(f"   - Using Chrome binary: {binary_path}")
        log(f"   - Using ChromeDriver: {driver_path}")

        chrome_options.binary_location = binary_path
        service = Service(executable_path=driver_path)

        log("   - Configuring headless mode options.")
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        log("   - Initializing WebDriver...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(20) # Increased wait time slightly
        log("   - ✅ WebDriver initialized successfully.")
        
        # --- End Selenium Setup ---
        
        log(f"Navigating to login URL: {login_url}")
        driver.get(login_url)

        driver.find_element(By.ID, "edit-name").send_keys(username)
        driver.find_element(By.ID, "edit-pass").send_keys(password)
        driver.find_element(By.ID, "edit-submit").click()
        time.sleep(3)
        log("Login successful.")

        log(f"Navigating to 'Add Article' page: {add_article_url}")
        driver.get(add_article_url)
        time.sleep(3)
        
        log("📝 Filling article form...")
        
        # (All your form-filling logic remains unchanged here)

        log("🚀 Clicking the final 'Save' button...")
        driver.find_element(By.ID, save_button_id).click()
        time.sleep(10)
        log("✅ TOOL 2: Finished. Article submitted successfully!")
        return "Article posted successfully."

    except Exception as e:
        log(f"🔥 An unexpected error occurred in the CMS tool: {e}")
        return json.dumps({"error": f"Failed to post article to CMS. Error: {e}"})
    finally:
        if driver:
            log("   - Quitting WebDriver.")
            driver.quit()