# File: my_framework/app/server.py

# --- FIX FOR LOCAL DEVELOPMENT ---
# This code adds the project's root directory to the Python path
# so that it can find the 'my_framework' module.
# It has no effect when running on Render, so it's safe to include.
import sys
import os
from dotenv import load_dotenv

# Get the absolute path of the directory containing this script (app)
# and then get the parent directory (the project root)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')

# Add the 'src' directory to the Python path
if src_path not in sys.path:
    sys.path.insert(0, src_path)
# --- END OF FIX ---

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import threading
import json
import pprint
from my_framework.apps.journalist import generate_article_and_metadata, post_article_to_cms, add_metadata_to_article

app = FastAPI(
    title="Advanced AI Journalist Orchestrator",
    version="1.4",
    description="An API that runs a robust, direct workflow for generating and posting articles."
)

# --- Diagnostic Code ---
print("--- Python Application Environment Variables ---")
pprint.pprint(dict(os.environ))
print("----------------------------------------------")


def journalist_workflow(config_data: dict):
    """
    This function runs the complete, step-by-step workflow with improved error checking.
    It now handles both generating articles and submitting pre-written ones.
    """
    print("--- Starting Direct Journalist Workflow ---")
    active_tab = config_data.get('active_tab', 'generate')
    
    for i in range(1, 4):
        article_json_string = None
        
        if active_tab == 'generate':
            source_url = config_data.get(f'source_url_{i}')
            prompt = config_data.get(f'prompt_{i}')
            if not source_url or not prompt:
                continue
            print(f"\n--- Processing Article {i} (Generating from URL) ---")
            try:
                print(f"   - Calling 'generate_article_and_metadata' tool...")
                article_json_string = generate_article_and_metadata.run(
                    source_url=source_url,
                    user_prompt=prompt,
                    ai_model=config_data.get('ai_model'),
                    api_key=config_data.get('openai_api_key')
                )
            except Exception as e:
                print(f"   - 🔥 A critical error occurred during generation: {e}")
                continue
        
        elif active_tab == 'submit':
            article_text = config_data.get(f'article_text_{i}')
            if not article_text:
                continue
            print(f"\n--- Processing Article {i} (Submitting Pre-written Text) ---")
            try:
                print(f"   - Calling 'add_metadata_to_article' tool...")
                article_json_string = add_metadata_to_article.run(
                    article_text=article_text,
                    api_key=config_data.get('openai_api_key')
                )
            except Exception as e:
                print(f"   - 🔥 A critical error occurred during metadata generation: {e}")
                continue

        # --- Common processing and posting logic ---
        if article_json_string:
            print("\n--- 🤖 Generated Article JSON from AI 🤖 ---\n")
            print(article_json_string)
            print("\n--------------------------------------------\n")
            
            try:
                article_data = json.loads(article_json_string)
                if 'error' in article_data:
                    print(f"   - 🔥 Error from generation tool. Halting process for this article.")
                    print(f"   - 🔥 Reason: {article_data['error']}")
                    continue
                print("   - ✅ AI processing successful. Proceeding to post.")
            except Exception as e:
                print(f"   - 🔥 Failed to parse JSON from AI tool: {e}")
                continue

            try:
                print("   - Calling 'post_article_to_cms' tool...")
                post_result = post_article_to_cms.run(
                    article_json_string=article_json_string,
                    login_url=config_data.get('login_url'),
                    username=config_data.get('username'),
                    password=config_data.get('password'),
                    add_article_url=config_data.get('add_article_url'),
                    save_button_id=config_data.get('save_button_id')
                )
                print(f"   - ✅ Posting tool finished with result: {post_result}")
            except Exception as e:
                print(f"   - 🔥 A critical error occurred during posting: {e}")
                continue
            
    print("\n--- ✅✅✅ Full Workflow Complete ✅✅✅ ---")


@app.post("/invoke", summary="Run the full journalist workflow")
async def invoke_run(request: dict):
    config_data = request.get("input", request)
    print("API: Received request. Starting workflow in a background thread.")
    thread = threading.Thread(target=journalist_workflow, args=(config_data,))
    thread.daemon = True
    thread.start()
    return {"output": "Successfully started the journalist workflow. Check the server logs for detailed progress."}

@app.get("/", response_class=FileResponse)
async def read_index():
    """Serves the main HTML page to the user's browser."""
    # This path is relative to the `my_framework` directory where you run the server
    return os.path.join(os.path.dirname(__file__), 'templates', 'index.html')