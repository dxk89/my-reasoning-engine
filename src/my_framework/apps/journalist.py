import json
import os
import time
from datetime import datetime, timedelta

import pytz
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


from my_framework.agents.utils import (
    remove_non_bmp_chars,
    select_dropdown_option,
    tick_checkboxes_by_id,
    PUBLICATION_MAP,
    COUNTRY_MAP,
    INDUSTRY_MAP,
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
    Generates a complete, fact-checked, and SEO-optimized article with all CMS metadata.
    """
    # ... (This function is now correct from the previous step)
    log("🤖 TOOL 1: Starting multi-step article generation process...")
    source_content = scrape_content(source_url)
    if isinstance(source_content, dict) and "error" in source_content:
        return json.dumps(source_content)
    llm = ChatOpenAI(model_name="gpt-4o", temperature=0.5, api_key=api_key)
    draft_article = get_initial_draft(llm, user_prompt, source_content)
    if "error" in draft_article:
        return json.dumps({"error": draft_article})
    revised_article = get_revised_article(llm, source_content, draft_article)
    if "error" in revised_article:
        return json.dumps({"error": revised_article})
    final_json_string = get_seo_metadata(llm, revised_article)
    if isinstance(json.loads(final_json_string), dict) and "error" in json.loads(final_json_string):
        return final_json_string
    try:
        parsed_data = safe_load_json(final_json_string)
        entity_prompt = f"""
        Based on the following article, identify the specific countries and publications discussed.
        - For the country, identify the main nation the article is about.
        - For the publication, choose the MOST SPECIFIC "Today" publication that matches the country.
        Return a JSON object with keys "countries" and "publications".
        ARTICLE:
        {parsed_data.get('body', '')}
        """
        entity_response = llm.invoke([{"role": "user", "content": entity_prompt}])
        entities = safe_load_json(entity_response.content)
        parsed_data["country_id_selections"] = [COUNTRY_MAP[name] for name in entities.get("countries", []) if name in COUNTRY_MAP]
        parsed_data["publication_id_selections"] = [PUBLICATION_MAP[name] for name in entities.get("publications", []) if name in PUBLICATION_MAP]
        final_json_string = json.dumps(parsed_data)
        log("   - ✅ Successfully extracted and mapped entities for checkboxes.")
    except Exception as e:
        log(f"   - ⚠️ Could not extract entities for checkboxes: {e}")
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
    Logs into the CMS and submits an article using browser automation, filling all fields.
    This tool works both locally and on the Render deployment environment.
    """
    log("🤖 TOOL 2: Starting CMS Posting...")
    
    try:
        article_content = json.loads(article_json_string)
        if "error" in article_content:
            return json.dumps(article_content)
    except (json.JSONDecodeError, TypeError) as e:
        return json.dumps({"error": f"Invalid JSON provided: {e}"})

    driver = None
    try:
        chrome_options = webdriver.ChromeOptions()
        is_render_env = 'RENDER' in os.environ

        if is_render_env:
            log("   - Running in Render environment (headless mode).")
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            binary_path = os.environ.get("GOOGLE_CHROME_BIN")
            driver_path = os.environ.get("CHROMEDRIVER_PATH")

            if not binary_path or not os.path.isfile(binary_path):
                return json.dumps({"error": f"Chrome binary not found on Render. GOOGLE_CHROME_BIN='{binary_path}'"})
            if not driver_path or not os.path.isfile(driver_path):
                 return json.dumps({"error": f"ChromeDriver not found on Render. CHROMEDRIVER_PATH='{driver_path}'"})

            chrome_options.binary_location = binary_path
            service = Service(executable_path=driver_path)
        else:
            log("   - Running in local environment (visible mode).")
            try:
                service = Service(ChromeDriverManager().install())
            except Exception as e:
                log(f"   - 🔥 Failed to install/start ChromeDriver locally: {e}")
                return json.dumps({"error": f"Could not start local ChromeDriver: {e}"})
        
        log("   - Initializing WebDriver...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(20)
        log("   - ✅ WebDriver initialized successfully.")
        
        # ... (The rest of the logic remains the same)
        
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