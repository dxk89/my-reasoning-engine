# File: src/my_framework/apps/journalist.py

import os
import json
import time
# ... (all other imports)

from my_framework.models.openai import ChatOpenAI
from my_framework.core.schemas import HumanMessage

def log(message):
    print(f"   - {message}", flush=True)

# (Your large MAP dictionaries and helper functions go here...)
# ...

@tool
def generate_article_and_metadata(source_url: str, user_prompt: str, ai_model: str, api_key: str) -> str:
    log("🤖 TOOL 1: Starting multi-step article and metadata generation...")

    # --- Step 1: Scrape Content (Memory Optimized) ---
    log(f"   -> Step 1.1: Scraping content from {source_url}...")
    try:
        response = requests.get(source_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=90)
        response.raise_for_status()
        log("   -> Step 1.2: Web page request successful.")
        soup = BeautifulSoup(response.text, 'html.parser')

        # --- THIS IS THE FIX ---
        # Instead of getting all paragraphs, we limit it to the first 30.
        # This prevents loading massive pages into memory and causing a crash.
        paragraphs = soup.find_all('p', limit=30)
        source_content = ' '.join(p.get_text() for p in paragraphs)
        # --------------------
        
        log(f"   -> Step 1.3: Successfully scraped {len(paragraphs)} paragraphs ({len(source_content)} characters).")
    except Exception as e:
        log(f"   -> 🔥 Step 1 FAILED: URL scraping failed: {e}")
        return json.dumps({"error": f"URL scraping failed: {e}"})

    # (The rest of the function remains exactly the same)
    # ...