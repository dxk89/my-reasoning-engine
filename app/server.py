# File: my_framework/app/server.py
from dotenv import load_dotenv
load_dotenv() # This line is critical: it loads the .env file created by the build script.

from fastapi import FastAPI, HTTPException
import threading
import json
import os
import pprint

# --- Diagnostic Code ---
# This will print all the environment variables that the Python app can see.
# After this fix, you should see GOOGLE_CHROME_BIN in this list.
print("--- Python Application Environment Variables ---")
pprint.pprint(dict(os.environ))
print("----------------------------------------------")

from my_framework.apps.journalist import generate_article_and_metadata, post_article_to_cms

app = FastAPI(
    title="Advanced AI Journalist Orchestrator",
    version="1.9",
    description="An API that runs a robust, direct workflow for generating and posting articles."
)

def journalist_workflow(config_data: dict):
    """
    This function runs the complete, step-by-step workflow with improved error checking.
    """
    print("--- Starting Direct Journalist Workflow ---")
    
    for i in range(1, 4):
        source_url = config_data.get(f'source_url_{i}')
        prompt = config_data.get(f'prompt_{i}')
        
        if not source_url or not prompt:
            continue
            
        print(f"\n--- Processing Article {i} ---")
        
        article_json_string = None
        try:
            print(f"   - Calling SMART 'generate_article_and_metadata' tool...")
            article_json_string = generate_article_and_metadata.run(
                source_url=source_url,
                user_prompt=prompt,
                ai_model=config_data.get('ai_model'),
                api_key=config_data.get('openai_api_key') or config_data.get('gemini_api_key')
            )
            
            print("\n--- 🤖 Generated Article JSON from AI 🤖 ---\n")
            print(article_json_string)
            print("\n--------------------------------------------\n")
            
            article_data = json.loads(article_json_string)
            
            if 'error' in article_data:
                print(f"   - 🔥 Error from generation tool. Halting process for this article.")
                print(f"   - 🔥 Reason: {article_data['error']}")
                continue
                
            print("   - ✅ Smart article generation successful. Proceeding to post.")

        except Exception as e:
            print(f"   - 🔥 A critical error occurred during generation: {e}")
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

@app.get("/", summary="Health Check")
def read_root():
    return {"status": "ok"}