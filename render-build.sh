#!/usr/bin/env bash
# exit on any error
set -o errexit

STORAGE_DIR="/opt/render/project/.render"
CHROME_VERSION="140.0.7339.185"

# Download and extract Chrome if not already present
if [[ ! -d "$STORAGE_DIR/chrome/chrome-linux64" ]]; then
  echo "...Installing Chrome"
  mkdir -p "$STORAGE_DIR/chrome"
  cd "$STORAGE_DIR/chrome"
  wget -q -O chrome-linux64.zip \
    "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chrome-linux64.zip"
  unzip -q chrome-linux64.zip
  rm chrome-linux64.zip
else
  echo "...Using cached Chrome"
fi

# Install the matching ChromeDriver
if [[ ! -f "$STORAGE_DIR/chromedriver/chromedriver" ]]; then
  echo "...Installing ChromeDriver"
  mkdir -p "$STORAGE_DIR/chromedriver"
  cd "$STORAGE_DIR/chromedriver"
  wget -q -O chromedriver-linux64.zip \
    "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip"
  unzip -q chromedriver-linux64.zip
  mv chromedriver-linux64/chromedriver .
  rm -rf chromedriver-linux64 chromedriver-linux64.zip
else
  echo "...Using cached ChromeDriver"
fi

# --- NEW LINES START HERE ---
# Find the exact path to the chrome binary and save it for the start command
CHROME_BIN=$(find "$STORAGE_DIR/chrome" -type f -name "chrome" | head -n 1)
if [[ -n "$CHROME_BIN" ]]; then
  echo "Found Chrome binary at $CHROME_BIN"
  # Save the path to a file that the startCommand can read
  echo -n "$CHROME_BIN" > "$STORAGE_DIR/.render-chrome-path"
fi
# --- NEW LINES END HERE ---

cd "$HOME/project/src"
pip install -r requirements.txt