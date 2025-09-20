# File: src/my_framework/apps/journalist.py

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
        
        # Map names from the single AI response to IDs
        parsed_data["country_id_selections"] = [COUNTRY_MAP[name] for name in parsed_data.get("countries", []) if name in COUNTRY_MAP]
        parsed_data["publication_id_selections"] = [PUBLICATION_MAP[name] for name in parsed_data.get("publications", []) if name in PUBLICATION_MAP]
        parsed_data["industry_id_selections"] = [INDUSTRY_MAP[name] for name in parsed_data.get("industries", []) if name in INDUSTRY_MAP]

        # Rename keys to match what the CMS tool expects
        parsed_data["title_value"] = parsed_data.pop("title", "")
        parsed_data["body_value"] = parsed_data.pop("body", "")

        final_json_string = json.dumps(parsed_data)
        log("   - ✅ Successfully extracted and mapped all entities from single AI call.")
        
    except Exception as e:
        log(f"   - ⚠️ Could not process data from AI call: {e}")
        return json.dumps({"error": f"Failed to process data from AI call: {e}"})

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

    # --- Validation Check ---
    required_fields = ["title_value", "body_value", "publication_id_selections"]
    missing_fields = [field for field in required_fields if not article_content.get(field)]
    if missing_fields:
        return json.dumps({"error": f"Missing required fields: {', '.join(missing_fields)}"})


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

        # Primary Content & Metadata
        driver.find_element(By.ID, "edit-title").send_keys(remove_non_bmp_chars(article_content.get('title_value', '')))
        driver.find_element(By.ID, "edit-field-weekly-title-und-0-value").send_keys(remove_non_bmp_chars(article_content.get('weekly_title_value', '')))
        select_dropdown_option(driver, 'edit-field-machine-written-und', article_content.get('machine_written_value'), log, "Machine written")
        driver.find_element(By.ID, "edit-field-bylines-und-0-field-byline-und").send_keys(remove_non_bmp_chars(article_content.get('byline_value', '')))
        driver.find_element(By.ID, "edit-field-website-callout-und-0-value").send_keys(remove_non_bmp_chars(article_content.get('website_callout_value', '')))
        driver.find_element(By.ID, "edit-field-social-media-callout-und-0-value").send_keys(remove_non_bmp_chars(article_content.get('social_media_callout_value', '')))
        
        body_content = remove_non_bmp_chars(article_content.get('body_value', ''))
        escaped_body = json.dumps(body_content)
        driver.execute_script(f"CKEDITOR.instances['edit-body-und-0-value'].setData({escaped_body});")
        
        # Checkbox selections
        tick_checkboxes_by_id(driver, article_content.get('country_id_selections'), log)
        tick_checkboxes_by_id(driver, article_content.get('publication_id_selections'), log)
        tick_checkboxes_by_id(driver, article_content.get('industry_id_selections'), log)

        # Dropdown selections
        select_dropdown_option(driver, 'edit-field-subject-und', article_content.get('daily_subject_value'), log, "Daily Publications Subject")
        select_dropdown_option(driver, 'edit-field-ballot-box-und', article_content.get('ballot_box_value'), log, "Ballot Box")
        select_dropdown_option(driver, 'edit-field-key-und', article_content.get('key_point_value'), log, "Key Point")
        select_dropdown_option(driver, 'edit-field-africa-daily-section-und', article_content.get('africa_daily_section_value'), log, "Africa Daily Section")
        select_dropdown_option(driver, 'edit-field-southeast-europe-today-sec-und', article_content.get('southeast_europe_today_sections_value'), log, "Southeast Europe Today Sections")
        select_dropdown_option(driver, 'edit-field-cee-middle-east-africa-tod-und', article_content.get('cee_news_watch_country_sections_value'), log, "CEE News Watch Country Sections")
        select_dropdown_option(driver, 'edit-field-middle-east-n-africa-today-und', article_content.get('n_africa_today_section_value'), log, "N.Africa Today Section")
        select_dropdown_option(driver, 'edit-field-middle-east-today-section-und', article_content.get('middle_east_today_section_value'), log, "Middle East Today Section")
        select_dropdown_option(driver, 'edit-field-baltic-states-today-sectio-und', article_content.get('baltic_states_today_sections_value'), log, "Baltic States Today Sections")
        select_dropdown_option(driver, 'edit-field-asia-today-sections-und', article_content.get('asia_today_sections_value'), log, "Asia Today Sections")
        select_dropdown_option(driver, 'edit-field-latam-today-und', article_content.get('latam_today_value'), log, "LatAm Today")

        # Workflow & System Settings
        driver.find_element(By.ID, "edit-metatags-und-abstract-value").send_keys(remove_non_bmp_chars(article_content.get('abstract_value', '')))
        driver.find_element(By.ID, "edit-metatags-und-keywords-value").send_keys(remove_non_bmp_chars(article_content.get('keywords_value', '')))
        driver.find_element(By.ID, "edit-metatags-und-news-keywords-value").send_keys(remove_non_bmp_chars(article_content.get('google_news_keywords_value', '')))
        
        if save_button_id:
            log("🚀 Clicking the final 'Save' button...")
            driver.find_element(By.ID, save_button_id).click()
            time.sleep(10)
            log("✅ TOOL 2: Finished. Article submitted successfully!")
            return "Article posted successfully."
        else:
            log("⚠️ Save button ID not configured. Form filled but not saved.")
            return "Form filled but not saved as no save button ID was provided."

    except Exception as e:
        log(f"🔥 An unexpected error occurred in the CMS tool: {e}")
        return json.dumps({"error": f"Failed to post article to CMS. Error: {e}"})
    finally:
        if driver:
            log("   - Quitting WebDriver.")
            driver.quit()