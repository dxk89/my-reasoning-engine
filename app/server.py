# File: my_framework/app/server.py

import sys
import os
from dotenv import load_dotenv

# This is a more robust way to add project directories to the python path
# It should work both locally and on Render
app_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(app_dir, '..'))
src_path = os.path.join(project_root, 'src')
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

load_dotenv()

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import FileResponse
import threading
import json
import pprint
import logging
import asyncio
import queue
from my_framework.apps.journalist import generate_article_and_metadata, post_article_to_cms, add_metadata_to_article

# --- Thread-Safe WebSocket Log Handler ---
class QueueLogHandler(logging.Handler):
    def __init__(self, q):
        super().__init__()
        self.queue = q

    def emit(self, record):
        self.queue.put(self.format(record))

# --- Setup Logging ---
log_queue = queue.Queue()
log_handler = QueueLogHandler(log_queue)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# Remove any default handlers to avoid duplicate console logs
for handler in logger.handlers[:]:
    logger.removeHandler(handler)
logger.addHandler(log_handler)


# --- WebSocket Connections ---
active_connections: list[WebSocket] = []

async def log_sender():
    """Continuously checks the queue and sends logs to all connected clients."""
    while True:
        try:
            log_entry = log_queue.get_nowait()
            for connection in active_connections:
                await connection.send_text(log_entry)
        except queue.Empty:
            await asyncio.sleep(0.1) # Wait a bit if the queue is empty

app = FastAPI(
    title="Advanced AI Journalist Orchestrator",
    version="1.4",
    description="An API that runs a robust, direct workflow for generating and posting articles."
)

@app.on_event("startup")
async def startup_event():
    """Start the log sender task when the application starts."""
    asyncio.create_task(log_sender())

# --- Diagnostic Code ---
print("--- Python Application Environment Variables ---")
pprint.pprint(dict(os.environ))
print("----------------------------------------------")


def journalist_workflow(config_data: dict):
    """
    This function runs the complete, step-by-step workflow with improved error checking.
    It now handles both generating articles and submitting pre-written ones.
    """
    logging.info("--- Starting Direct Journalist Workflow ---")
    active_tab = config_data.get('active_tab', 'generate')
    
    for i in range(1, 4):
        article_json_string = None
        
        if active_tab == 'generate':
            source_url = config_data.get(f'source_url_{i}')
            prompt = config_data.get(f'prompt_{i}')
            if not source_url or not prompt:
                continue
            logging.info(f"\n--- Processing Article {i} (Generating from URL) ---")
            try:
                logging.info(f"   - Calling 'generate_article_and_metadata' tool...")
                article_json_string = generate_article_and_metadata.run(
                    source_url=source_url,
                    user_prompt=prompt,
                    ai_model=config_data.get('ai_model'),
                    api_key=config_data.get('openai_api_key')
                )
            except Exception as e:
                logging.error(f"   - 🔥 A critical error occurred during generation: {e}")
                continue
        
        elif active_tab == 'submit':
            article_text = config_data.get(f'article_text_{i}')
            if not article_text:
                continue
            logging.info(f"\n--- Processing Article {i} (Submitting Pre-written Text) ---")
            try:
                logging.info(f"   - Calling 'add_metadata_to_article' tool...")
                article_json_string = add_metadata_to_article.run(
                    article_text=article_text,
                    api_key=config_data.get('openai_api_key')
                )
            except Exception as e:
                logging.error(f"   - 🔥 A critical error occurred during metadata generation: {e}")
                continue

        # --- Common processing and posting logic ---
        if article_json_string:
            logging.info("\n--- 🤖 Generated Article JSON from AI 🤖 ---\n")
            logging.info(article_json_string)
            logging.info("\n--------------------------------------------\n")
            
            try:
                article_data = json.loads(article_json_string)
                if 'error' in article_data:
                    logging.error(f"   - 🔥 Error from generation tool. Halting process for this article.")
                    logging.error(f"   - 🔥 Reason: {article_data['error']}")
                    continue
                logging.info("   - ✅ AI processing successful. Proceeding to post.")
            except Exception as e:
                logging.error(f"   - 🔥 Failed to parse JSON from AI tool: {e}")
                continue

            try:
                logging.info("   - Calling 'post_article_to_cms' tool...")
                post_result = post_article_to_cms.run(
                    article_json_string=article_json_string,
                    login_url=config_data.get('login_url'),
                    username=config_data.get('username'),
                    password=config_data.get('password'),
                    add_article_url=config_data.get('add_article_url'),
                    save_button_id=config_data.get('save_button_id')
                )
                logging.info(f"   - ✅ Posting tool finished with result: {post_result}")
            except Exception as e:
                logging.error(f"   - 🔥 A critical error occurred during posting: {e}")
                continue
            
    logging.info("\n--- ✅✅✅ Full Workflow Complete ✅✅✅ ---")


@app.post("/invoke", summary="Run the full journalist workflow")
async def invoke_run(request: dict):
    config_data = request.get("input", request)
    logging.info("API: Received request. Starting workflow in a background thread.")
    thread = threading.Thread(target=journalist_workflow, args=(config_data,))
    thread.daemon = True
    thread.start()
    return {"output": "Starting Process"}

@app.get("/", response_class=FileResponse)
async def read_index():
    """Serves the main HTML page to the user's browser."""
    # This path is relative to the `my_framework` directory where you run the server
    return os.path.join(os.path.dirname(__file__), 'templates', 'index.html')

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        active_connections.remove(websocket)