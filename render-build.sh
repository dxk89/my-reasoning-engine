#!/usr/-bin/env bash
# exit on any error
set -o errexit

STORAGE_DIR="/opt/render/project/.render"
CHROME_VERSION="140.0.7339.185" # Explicitly set the version

# Download and extract Chrome if not already present
if [[ ! -d "$STORAGE_DIR/chrome/chrome-linux64" ]]; then
  echo "...Installing Chrome"
  mkdir -p "$STORAGE_DIR/chrome"
  cd "$STORAGE_DIR/chrome"
  wget -q -O chrome-linux64.zip \
    "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chrome-linux64.zip"
  unzip -q chrome-linux64.zip
  rm chrome-linux64.zip
  cd "$HOME/project/src"
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
  # Move the driver to the current directory
  mv chromedriver-linux64/chromedriver .
  rm -rf chromedriver-linux64 chromedriver-linux64.zip
  cd "$HOME/project/src"
else
  echo "...Using cached ChromeDriver"
fi