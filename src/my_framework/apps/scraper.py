# File: src/my_framework/apps/scraper.py

import requests
from bs4 import BeautifulSoup
import json

def log(message):
    print(f"   - {message}", flush=True)

def scrape_content(source_url: str) -> str:
    """
    Scrapes the main article content from a given URL by intelligently finding the
    primary content container.
    """
    log(f"-> Scraping content from {source_url}...")
    try:
        response = requests.get(source_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=90)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # --- New Intelligent Content Extraction Logic ---
        # Remove common non-content elements to reduce noise
        for selector in ['header', 'footer', 'nav', 'script', 'style', '.sidebar', '[role="navigation"]', '[class*="comments"]']:
            for element in soup.select(selector):
                element.decompose()

        # Find the element with the most paragraph text, which is likely the main article
        main_content = max(soup.find_all('div'), key=lambda tag: len(" ".join(p.get_text() for p in tag.find_all('p'))), default=soup.body)
        
        if not main_content:
            log("   - ⚠️ No specific content container found, falling back to full body.")
            main_content = soup.body
            
        paragraphs = main_content.find_all('p', recursive=False) # Only direct children
        if len(paragraphs) < 3: # If not enough direct paragraphs, search deeper
            paragraphs = main_content.find_all('p')

        source_content = '\n\n'.join(p.get_text().strip() for p in paragraphs if p.get_text().strip())


        if not source_content.strip():
            log("-> 🔥 URL scraping failed: No paragraph content found in the located container.")
            return json.dumps({"error": "URL scraping failed: No paragraph content found."})

        log(f"-> Scraping successful ({len(source_content)} characters).")
        return source_content

    except requests.exceptions.RequestException as e:
        log(f"-> 🔥 URL scraping failed: Network error - {e}")
        return json.dumps({"error": f"URL scraping failed: Could not connect to the URL. {e}"})
    except Exception as e:
        log(f"-> 🔥 URL scraping failed: An unexpected error occurred - {e}")
        return json.dumps({"error": f"URL scraping failed: {e}"})