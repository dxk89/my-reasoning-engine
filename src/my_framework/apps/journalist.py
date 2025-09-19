import json
import os
import time
from datetime import datetime, timedelta

import pytz
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

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

    # Normalise the JSON one more time to ensure it is valid and lists are lists
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
    This function uses Selenium to automate the browser. It requires that a Chrome
    binary be installed in the Render environment. The `render-build.sh` script
    installs Chrome into `/opt/render/project/.render/chrome/opt/google/chrome`.
    The start command in `render.yaml` should set the `GOOGLE_CHROME_BIN`
    environment variable to point to the Chrome binary and add its directory
    to the PATH. If the environment variable is set, the Chrome driver will
    automatically pick it up; otherwise, we fall back to the default path.
    """

    log("🤖 TOOL 2: Starting CMS Posting...")

    # ------------------------------------------------------------------
    # Validate inputs
    # ------------------------------------------------------------------
    if not all([article_json_string, login_url, username, password, add_article_url]):
        error_message = (
            "Missing required parameters for posting to the CMS."
        )
        log(error_message)
        return json.dumps({"error": error_message})

    # Try strict JSON parse first; fall back to safe_load_json if needed
    try:
        article_content = json.loads(article_json_string)
    except json.JSONDecodeError:
        try:
            article_content = safe_load_json(article_json_string)
        except Exception as exc:
            error_message = f"Invalid article JSON supplied: {exc}"
            log(error_message)
            return json.dumps({"error": error_message})

    if not isinstance(article_content, dict):
        error_message = "Article payload must be a JSON object."
        log(error_message)
        return json.dumps({"error": error_message})

    if "error" in article_content:
        error_message = (
            "Cannot post article because the payload contains an error: "
            f"{article_content['error']}"
        )
        log(error_message)
        return json.dumps({"error": error_message})

    # Helper to set CKEditor fields safely.
    def _set_ckeditor_content(driver, element_id, html_value):
        if not html_value:
            return
        try:
            driver.execute_script(
                """
                const elementId = arguments[0];
                const value = arguments[1];
                if (window.CKEDITOR && CKEDITOR.instances && CKEDITOR.instances[elementId]) {
                    CKEDITOR.instances[elementId].setData(value);
                    CKEDITOR.instances[elementId].updateElement();
                } else {
                    const el = document.getElementById(elementId);
                    if (el) {
                        el.value = value;
                    }
                }
                """,
                element_id,
                html_value,
            )
            log(f"   - Filled rich text field '{element_id}'.")
        except Exception as exc:  # pragma: no cover - best effort logging
            log(f"   - ⚠️ Could not populate rich text field '{element_id}': {exc}")

    def _fill_text_field(driver, field_id, value, description):
        if not value:
            return
        try:
            element = driver.find_element(By.ID, field_id)
            element.clear()
            element.send_keys(remove_non_bmp_chars(value))
            log(f"   - Filled {description}.")
        except Exception as exc:  # pragma: no cover - best effort logging
            log(f"   - ⚠️ Could not fill {description} (field '{field_id}'): {exc}")

    driver = None
    is_headless = bool(os.environ.get("RENDER") or os.environ.get("CI"))

    try:
        chrome_options = webdriver.ChromeOptions()
        # If a chrome binary location is provided, set it.  This allows
        # Selenium to find the chrome executable when it is not installed
        # system-wide.  The start command in render.yaml should set
        # GOOGLE_CHROME_BIN to the full path of the installed chrome.
        # Determine the path to the Chrome binary.  By default we
        # assume Chrome was installed into Render’s persistent storage
        # using the Chrome‑for‑Testing archive (see render-build.sh).
        # The environment variable GOOGLE_CHROME_BIN can override this
        # default.  If neither is set, we fall back to the older
        # google-chrome path for backwards compatibility.
        binary_path = os.environ.get(
            "GOOGLE_CHROME_BIN",
            "/opt/render/project/.render/chrome/chrome-linux64/chrome"
        )
        if binary_path:
            chrome_options.binary_location = binary_path

        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        if is_headless or os.environ.get("HEADLESS_CHROME"):
            log("Running Chrome in headless mode.")
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
        else:
            log("Running Chrome with UI (non-headless).")

        # NOTE: Chrome must be installed in your Render environment.  See
        # the deployment instructions for details.
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(15)

        # --------------------------------------------------------------
        # Step 1: Log in
        # --------------------------------------------------------------
        log(f"Navigating to login URL: {login_url}")
        driver.get(login_url)

        try:
            driver.find_element(By.ID, "edit-name").send_keys(username)
            driver.find_element(By.ID, "edit-pass").send_keys(password)
            driver.find_element(By.ID, "edit-submit").click()
            log("   - Submitted login form.")
            time.sleep(3)
        except Exception as exc:
            error_message = f"Failed to submit login form: {exc}"
            log(error_message)
            return json.dumps({"error": error_message})

        # --------------------------------------------------------------
        # Step 2: Navigate to article creation page
        # --------------------------------------------------------------
        log(f"Navigating to Add Article URL: {add_article_url}")
        driver.get(add_article_url)
        time.sleep(3)

        # --------------------------------------------------------------
        # Step 3: Populate the form using article data
        # --------------------------------------------------------------
        title_value = article_content.get("title_value") or article_content.get("title")
        if title_value:
            try:
                title_input = driver.find_element(By.ID, "edit-title")
                title_input.clear()
                title_input.send_keys(remove_non_bmp_chars(title_value))
                log("   - Filled article title.")
            except Exception as exc:
                log(f"   - ⚠️ Could not populate title field: {exc}")

        body_value = article_content.get("body_value") or article_content.get("body")
        if body_value:
            _set_ckeditor_content(driver, "edit-body-und-0-value", body_value)

        # Optional metadata fields if available in the payload.
        text_field_map = {
            "weekly_title_value": (
                "edit-field-weekly-title-und-0-value",
                "weekly title",
            ),
            "website_callout_value": (
                "edit-field-website-callout-und-0-value",
                "website callout",
            ),
            "social_media_callout_value": (
                "edit-field-social-media-callout-und-0-value",
                "social media callout",
            ),
            "seo_title_value": (
                "edit-field-meta-title-und-0-value",
                "SEO title",
            ),
            "seo_description_value": (
                "edit-field-meta-description-und-0-value",
                "SEO description",
            ),
            "seo_description": (
                "edit-field-meta-description-und-0-value",
                "SEO description",
            ),
            "seo_keywords_value": (
                "edit-field-meta-keywords-und-0-value",
                "SEO keywords",
            ),
            "seo_keywords": (
                "edit-field-meta-keywords-und-0-value",
                "SEO keywords",
            ),
            "abstract_value": (
                "edit-field-summary-und-0-value",
                "abstract",
            ),
            "google_news_keywords_value": (
                "edit-field-google-news-keywords-und-0-value",
                "Google News keywords",
            ),
        }

        for payload_key, (field_id, description) in text_field_map.items():
            field_value = article_content.get(payload_key)
            if isinstance(field_value, list):
                field_value = ", ".join(str(item) for item in field_value if item)
            _fill_text_field(driver, field_id, field_value, description)

        hashtags = article_content.get("hashtags_value") or article_content.get("hashtags")
        if hashtags:
            if isinstance(hashtags, list):
                hashtags_value = ", ".join(hashtags)
            else:
                hashtags_value = str(hashtags)
            _fill_text_field(
                driver,
                "edit-field-hashtags-und-0-value",
                hashtags_value,
                "hashtags",
            )

        # Apply checkbox and dropdown helpers if provided.
        tick_checkboxes_by_id(
            driver,
            article_content.get("country_id_selections"),
            log,
        )
        tick_checkboxes_by_id(
            driver,
            article_content.get("publication_id_selections"),
            log,
        )
        select_dropdown_option(
            driver,
            "edit-field-subject-und",
            article_content.get("daily_subject_value"),
            log,
            "Daily Subject",
        )
        select_dropdown_option(
            driver,
            "edit-field-key-und",
            article_content.get("key_point_value"),
            log,
            "Key Point",
        )

        # Attempt to set scheduling dates to a sensible default.
        try:
            gmt = pytz.timezone("GMT")
            now_gmt = datetime.now(gmt)
            target_date = now_gmt + timedelta(days=1) if now_gmt.hour >= 7 else now_gmt
            target_date_str = target_date.strftime("%m/%d/%Y")
            for field_id in [
                "edit-field-date-und-0-value-datepicker-popup-0",
                "edit-field-sending-date-und-0-value-datepicker-popup-0",
                "edit-field-publication-date-time-und-0-value-datepicker-popup-0",
            ]:
                driver.execute_script(
                    """
                    const elementId = arguments[0];
                    const value = arguments[1];
                    const el = document.getElementById(elementId);
                    if (el) {
                        el.value = value;
                        el.dispatchEvent(new Event('change'));
                    }
                    """,
                    field_id,
                    target_date_str,
                )
            log(f"   - Set scheduling dates to {target_date_str}.")
        except Exception as exc:  # pragma: no cover - best effort logging
            log(f"   - ⚠️ Could not set scheduling dates: {exc}")

        # Allow direct mapping if article JSON includes explicit field IDs.
        form_fields = article_content.get("form_fields")
        if isinstance(form_fields, dict):
            for field_id, raw_value in form_fields.items():
                value = raw_value
                if isinstance(value, list):
                    value = ", ".join(str(item) for item in value if item)
                if isinstance(value, bool):
                    try:
                        element = driver.find_element(By.ID, field_id)
                        should_select = value
                        input_type = (element.get_attribute("type") or "").lower()
                        if input_type in {"checkbox", "radio"}:
                            is_selected = element.is_selected()
                            if should_select != is_selected:
                                driver.execute_script("arguments[0].click();", element)
                                log(f"   - Toggled field '{field_id}'.")
                        else:
                            element.clear()
                            element.send_keys("true" if value else "false")
                            log(f"   - Filled field '{field_id}'.")
                    except Exception as exc:  # pragma: no cover - best effort logging
                        log(f"   - ⚠️ Could not update field '{field_id}': {exc}")
                else:
                    _fill_text_field(
                        driver,
                        field_id,
                        str(value) if value is not None else "",
                        f"custom field '{field_id}'",
                    )

        # --------------------------------------------------------------
        # Step 4: Submit the form
        # --------------------------------------------------------------
        if not save_button_id:
            error_message = "Save button ID not provided."
            log(error_message)
            return json.dumps({"error": error_message})

        try:
            log("🚀 Clicking the save button...")
            driver.find_element(By.ID, save_button_id).click()
            time.sleep(5)
        except Exception as exc:
            error_message = f"Failed to click the save button: {exc}"
            log(error_message)
            return json.dumps({"error": error_message})

        log("✅ Article submission completed successfully.")
        return "Article posted successfully."

    except Exception as exc:
        error_message = f"Unexpected error while posting article: {exc}"
        log(error_message)
        return json.dumps({"error": error_message})
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass