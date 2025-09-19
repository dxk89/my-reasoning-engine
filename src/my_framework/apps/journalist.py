import json
import os
import time
from datetime import datetime, timedelta

import pytz
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException

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
    if "error" in final_json_string:
        return json.dumps({"error": final_json_string})
    
    # Add entity extraction for checkboxes
    try:
        parsed_data = safe_load_json(final_json_string)
        
        # LLM call to extract entities from the article body
        entity_prompt = f"""
        Based on the following article, identify the specific countries, publications, and industries discussed.
        Use the exact names as they appear in the text.
        Return a JSON object with keys "countries", "publications", and "industries", each containing a list of names.
        
        ARTICLE:
        {parsed_data.get('body', '')}
        """
        entity_response = llm.invoke([{"role": "user", "content": entity_prompt}])
        entities = safe_load_json(entity_response.content)

        # Map names to IDs using the dictionaries from utils.py
        parsed_data["country_id_selections"] = [COUNTRY_MAP[name] for name in entities.get("countries", []) if name in COUNTRY_MAP]
        parsed_data["publication_id_selections"] = [PUBLICATION_MAP[name] for name in entities.get("publications", []) if name in PUBLICATION_MAP]
        parsed_data["industry_id_selections"] = [INDUSTRY_MAP[name] for name in entities.get("industries", []) if name in INDUSTRY_MAP]

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
        binary_path = os.environ.get("GOOGLE_CHROME_BIN")
        driver_path = os.environ.get("CHROMEDRIVER_PATH")

        if not binary_path or not os.path.isfile(binary_path):
            return json.dumps({"error": f"Chrome binary not found. GOOGLE_CHROME_BIN='{binary_path}'"})
        
        if not driver_path or not os.path.isfile(driver_path):
             return json.dumps({"error": f"ChromeDriver not found. CHROMEDRIVER_PATH='{driver_path}'"})

        chrome_options.binary_location = binary_path
        service = Service(executable_path=driver_path)

        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(20)
        
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
        
        log("📝 Filling complete article form...")
        
        # --- EXPAND COLLAPSIBLE SECTIONS ---
        try:
            log("   - Expanding form sections...")
            driver.find_element(By.CSS_SELECTOR, "a[href='#edit-meta-tags']").click()
            time.sleep(1)
            log("   - ✅ Sections expanded.")
        except Exception as e:
            log(f"   - ⚠️ Could not expand all form sections: {e}")

        # --- HELPER FUNCTIONS FOR FORM FILLING ---
        def _fill_text_field(field_id, value, description):
            if not value:
                log(f"   - Skipping {description} (no value provided).")
                return
            try:
                element = driver.find_element(By.ID, field_id)
                element.clear()
                element.send_keys(remove_non_bmp_chars(value))
                log(f"   - ✅ Filled {description}.")
            except NoSuchElementException:
                log(f"   - ⚠️ {description} field with ID '{field_id}' not found.")
            except Exception as exc:
                log(f"   - ⚠️ Could not fill {description} (field '{field_id}'): {exc}")
        
        def _set_ckeditor_content(element_id, html_value, description):
             if not html_value:
                log(f"   - Skipping {description} (no value provided).")
                return
             try:
                driver.execute_script(f"CKEDITOR.instances['{element_id}'].setData({json.dumps(html_value)});")
                log(f"   - ✅ Filled {description}.")
             except Exception as e:
                log(f"   - ⚠️ Could not fill rich text editor for {description}: {e}")

        # --- COMPLETE FORM FILLING LOGIC ---
        _fill_text_field("edit-title", article_content.get("title"), "Article Title")
        _set_ckeditor_content("edit-body-und-0-value", article_content.get("body"), "Main Body Content")
        _fill_text_field("edit-field-weekly-title-und-0-value", article_content.get("weekly_title_value"), "Weekly Title")
        _fill_text_field("edit-field-website-callout-und-0-value", article_content.get("website_callout_value"), "Website Callout")
        _fill_text_field("edit-field-social-media-callout-und-0-value", article_content.get("social_media_callout_value"), "Social Media Callout")
        _set_ckeditor_content("edit-field-summary-und-0-value", article_content.get("abstract_value"), "Abstract/Summary")
        _fill_text_field("edit-field-meta-title-und-0-value", article_content.get("seo_title_value"), "SEO Title")
        _fill_text_field("edit-field-meta-description-und-0-value", article_content.get("seo_description"), "SEO Description")
        
        seo_keywords = article_content.get("seo_keywords")
        if seo_keywords:
            keywords_str = ", ".join(seo_keywords) if isinstance(seo_keywords, list) else seo_keywords
            _fill_text_field("edit-field-meta-keywords-und-0-value", keywords_str, "SEO Keywords")
            _fill_text_field("edit-field-google-news-keywords-und-0-value", keywords_str, "Google News Keywords")

        hashtags = article_content.get("hashtags")
        if hashtags:
            hashtags_str = ", ".join(h.lstrip('#') for h in hashtags) if isinstance(hashtags, list) else hashtags
            _fill_text_field("edit-field-hashtags-und-0-value", hashtags_str, "Hashtags")

        select_dropdown_option(driver, "edit-field-subject-und", article_content.get("daily_subject_value"), log, "Daily Subject")
        select_dropdown_option(driver, "edit-field-key-und", article_content.get("key_point_value"), log, "Key Point")

        # Tick Checkboxes
        tick_checkboxes_by_id(driver, article_content.get("publication_id_selections", []), log)
        tick_checkboxes_by_id(driver, article_content.get("country_id_selections", []), log)
        tick_checkboxes_by_id(driver, article_content.get("industry_id_selections", []), log)

        try:
            gmt = pytz.timezone("GMT")
            now_gmt = datetime.now(gmt)
            target_date = now_gmt + timedelta(days=1) if now_gmt.hour >= 7 else now_gmt
            target_date_str = target_date.strftime("%m/%d/%Y")
            for field_id in ["edit-field-date-und-0-value-datepicker-popup-0", "edit-field-sending-date-und-0-value-datepicker-popup-0", "edit-field-publication-date-time-und-0-value-datepicker-popup-0"]:
                driver.execute_script(f"document.getElementById('{field_id}').value = '{target_date_str}';")
            log(f"   - ✅ Set scheduling dates to {target_date_str}.")
        except Exception as exc:
            log(f"   - ⚠️ Could not set scheduling dates: {exc}")
        
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