from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import json

# ... other functions ...

def get_subjective_metadata_prompt(article_title, article_body):
    """Creates the prompt for the more creative metadata fields."""
    return f"""
    You are an expert sub-editor. Your response must be ONLY a valid JSON object.
    Based on the article, fill in the metadata using these keys: "weekly_title_value", "website_callout_value", "social_media_callout_value", "hashtags_value", "seo_title_value", "seo_description_value", "seo_keywords_value", "abstract_value", "google_news_keywords_value", "daily_subject_value", "key_point_value".

    RULES:
    - "abstract_value" should be a concise summary of the page's content, preferably 150 characters or less.
    - "hashtags_value" must be an ARRAY of up to 5 relevant hashtags as strings, each starting with '#'.
    - "google_news_keywords_value" should be a single string of comma-separated keywords.
    - "daily_subject_value": Choose ONE from ["Macroeconomic News", "Banking And Finance", "Companies and Industries", "Political"]
    - "key_point_value": Choose ONE from ["Yes", "No"].

    ARTICLE FOR ANALYSIS:
    Article Title: "{article_title}"
    Article Body: "{article_body}"
    """

# ... other functions ...