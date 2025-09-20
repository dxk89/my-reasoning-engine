# File: src/my_framework/apps/llm_calls.py

from my_framework.models.openai import ChatOpenAI, safe_load_json, normalize_article
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
        SystemMessage(content="You are an expert journalist. Your task is to write a professional, insightful, and "
                              "objective article based on the user's prompt and the provided source content. Focus on "
                              "financial, business, and political analysis of emerging markets."),
        HumanMessage(content=f"USER PROMPT: \"{user_prompt}\"\n\nSOURCE CONTENT:\n---\n{source_content}\n---\n\nWrite "
                             "the initial draft of the article now.")
    ]
    log("-> Sending request to LLM for initial draft...")
    draft_response = llm.invoke(draft_prompt)
    draft_article = draft_response.content
    log(f"-> Initial draft received ({len(draft_article)} characters).")
    return draft_article

def get_revised_article(llm: ChatOpenAI, source_content: str, draft_article: str) -> str:
    """
    Fact-checks and improves the style of the article.
    """
    log("-> Building prompt for fact-checking and stylistic improvements.")
    revision_prompt = [
        SystemMessage(content="You are a meticulous editor for intellinews.com. Your task is to review a draft article. "
                              "First, ensure every claim is fully supported by the provided SOURCE CONTENT, correcting "
                              "any inaccuracies. Second, refine the writing to match the professional, insightful, and "
                              "objective style of intellinews.com."),
        HumanMessage(content=f"SOURCE CONTENT:\n---\n{source_content}\n---\n\nDRAFT ARTICLE:\n---\n{draft_article}\n---\n\n"
                             "Please provide the revised, fact-checked, and stylistically improved article.")
    ]
    log("-> Sending request to LLM for revision...")
    revised_response = llm.invoke(revision_prompt)
    revised_article = revised_response.content
    log(f"-> Revised article received ({len(revised_article)} characters).")
    return revised_article

def get_seo_metadata(llm: ChatOpenAI, revised_article: str) -> str:
    """
    Generates comprehensive SEO and CMS metadata and formats the final output.
    """
    log("-> Building prompt for SEO optimization and JSON formatting.")
    seo_prompt = [
        SystemMessage(content="You are an expert sub-editor and content strategist. Your task is to take a final article and "
                              "prepare it for publishing by creating a title and all necessary CMS and SEO metadata. Format the "
                              "entire output as a single, valid JSON object."),
        HumanMessage(content=f"""
        Based on the following article, please perform these tasks and return a single JSON object with the specified keys.
        **Every field is mandatory.**

        ARTICLE:
        ---
        {revised_article}
        ---

        JSON OUTPUT REQUIREMENTS:
        1.  "title": A concise, compelling, SEO-friendly title. This field is required.
        2.  "body": The full revised article, formatted with HTML paragraph tags (`<p>`). This field is required.
        3.  "publications": An array of strings with the names of the MOST SPECIFIC relevant publications (e.g., ["Slovenia Today"]). This is required.
        4.  "countries": An array of strings with the exact names of countries mentioned (e.g., ["Slovenia"]).
        5.  "industries": An array of strings with the names of relevant industries (e.g., ["Renewables", "Banking"]).
        6.  "seo_description": A concise, engaging SEO meta description (155 characters max).
        7.  "seo_keywords": A comma-separated string of relevant SEO keywords.
        8.  "hashtags": An array of 3-5 relevant social media hashtags (e.g., ["#Slovenia", "#Aviation"]).
        9.  "weekly_title_value": A very short, punchy title for a weekly newsletter.
        10. "website_callout_value": A brief, attention-grabbing callout for the website's front page.
        11. "social_media_callout_value": A short, engaging phrase for social media posts (less than 250 characters).
        12. "abstract_value": A concise summary of the article's content (150 characters max).
        13. "google_news_keywords_value": A comma-separated string of relevant keywords for Google News.
        14. "daily_subject_value": **Required.** Choose ONE: "Macroeconomic News", "Banking And Finance", "Companies and Industries", or "Political".
        15. "key_point_value": **Required.** Choose ONE: "Yes" or "No".
        16. "machine_written_value": **Required.** Choose ONE: "Yes" or "No".
        17. "byline_value": The author's name, or "staff writer" if not available.
        18. "ballot_box_value": **Required.** Choose ONE: "Yes" or "No". If the article is about elections, this must be "Yes".
        19. "africa_daily_section_value": If relevant, choose ONE from ["- None -", "Top Story", "Politics", "Business & Finance", "Energy & Commodities"].
        20. "southeast_europe_today_sections_value": If relevant, choose ONE from ["- None -", "Top Story", "Business", "Finance", "Politics"].
        21. "cee_news_watch_country_sections_value": If relevant, choose ONE from ["- None -", "Top Story", "Macro", "Politics", "SME", "Events", "Thematic Investing", "bneInvestigator"].
        22. "n_africa_today_section_value": If relevant, choose ONE from ["- None -", "Top Story", "Politics", "Business & Finance", "Energy & Commodities"].
        23. "middle_east_today_section_value": If relevant, choose ONE from ["- None -", "Top Story", "Politics", "Business & Finance", "Energy & Commodities"].
        24. "baltic_states_today_sections_value": If relevant, choose ONE from ["- None -", "Top story", "Politics", "Economics", "Business"].
        25. "asia_today_sections_value": If relevant, choose ONE from ["- None -", "Top Story", "Politics", "Business & Finance", "Sanctions"].
        26. "latam_today_value": If relevant, choose ONE from ["- None -", "Top Story", "Politics", "Business & Finance", "Energy & Commodities"].
        """)
    ]
    log("-> Sending request to LLM for final SEO and formatting...")
    final_response = llm.invoke(seo_prompt)
    
    try:
        # Use the robust safe_load_json to handle potential formatting issues
        parsed_json = safe_load_json(final_response.content)
        final_json_string = json.dumps(parsed_json)
        log("-> Final JSON object received and validated.")
        return final_json_string
    except Exception as e:
        log(f"-> 🔥 Could not parse JSON from LLM response: {e}")
        return json.dumps({"error": f"Failed to parse SEO metadata from LLM: {e}", "raw_response": final_response.content})