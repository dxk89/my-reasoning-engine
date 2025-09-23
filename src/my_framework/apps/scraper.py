# File: src/my_framework/apps/scraper.py

import requests
from bs4 import BeautifulSoup
import json

def log(message):
    print(f"   - {message}", flush=True)

def scrape_content(source_url: str) -> str:
    """
    Scrapes the content from a given URL.
    """
    log(f"-> Scraping content from {source_url}...")
    try:
        response = requests.get(source_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=90)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p', limit=40)
        source_content = ' '.join(p.get_text() for p in paragraphs)

        if not source_content:
            log("-> 🔥 URL scraping failed: No content found.")
            return json.dumps({"error": "URL scraping failed: No content found."})

        log(f"-> Scraping successful ({len(source_content)} characters).")
        return source_content
    except Exception as e:
        log(f"-> 🔥 URL scraping failed: {e}")
        return json.dumps({"error": f"URL scraping failed: {e}"})