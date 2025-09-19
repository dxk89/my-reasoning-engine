#!/usr/bin/env bash
# exit on any error
set -o errexit

# This build script installs a headless Google Chrome binary into
# Render’s persistent storage so that Selenium can run a browser
# without a full desktop environment.  The binary is cached under
# /opt/render/project/.render/chrome so that subsequent builds can
# reuse it.  After installing Chrome you can run pip install to
# install your Python dependencies.

STORAGE_DIR="/opt/render/project/.render"
CHROME_DIR="$STORAGE_DIR/chrome"
DRIVER_DIR="$STORAGE_DIR/chromedriver"

# Download and extract Chrome into the storage directory if it’s not
# already present.
if [[ ! -d "$CHROME_DIR/chrome-linux64" && ! -d "$CHROME_DIR/opt/google/chrome" ]]; then
  echo "...Installing Chrome"
  mkdir -p "$CHROME_DIR"
  cd "$CHROME_DIR"
  
  # Fetch the latest stable version of Chrome for Testing
  LATEST_STABLE_VERSION=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions.json | jq -r .channels.Stable.version)
  
  if [ -n "$LATEST_STABLE_VERSION" ]; then
    echo "...Downloading Chrome for Testing version $LATEST_STABLE_VERSION"
    CHROME_URL="https://storage.googleapis.com/chrome-for-testing-public/$LATEST_STABLE_VERSION/linux64/chrome-linux64.zip"
    wget -q -O chrome-linux64.zip "$CHROME_URL"
    unzip -q chrome-linux64.zip
    rm chrome-linux64.zip
  else
    echo "...Could not determine latest Chrome for Testing version. Falling back to .deb package."
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    ar x google-chrome-stable_current_amd64.deb
    tar -xf data.tar.*
    rm google-chrome-stable_current_amd64.deb control.tar.* data.tar.* debian-binary
  fi
  
  cd "$HOME/project/src"
else
  echo "...Using cached Chrome"
fi

# Install a matching ChromeDriver
if [[ ! -f "$DRIVER_DIR/chromedriver" ]]; then
  echo "...Installing ChromeDriver"
  mkdir -p "$DRIVER_DIR"
  cd "$DRIVER_DIR"
  
  # Fetch the corresponding ChromeDriver for the installed Chrome version
  if [ -n "$LATEST_STABLE_VERSION" ]; then
    DRIVER_URL="https://storage.googleapis.com/chrome-for-testing-public/$LATEST_STABLE_VERSION/linux64/chromedriver-linux64.zip"
    echo "...Downloading ChromeDriver version $LATEST_STABLE_VERSION"
    wget -q -O chromedriver-linux64.zip "$DRIVER_URL"
    unzip -q chromedriver-linux64.zip
    # Move the driver to the top level of the directory
    mv chromedriver-linux64/chromedriver .
    rm -rf chromedriver-linux64 chromedriver-linux64.zip
  else
    echo "...Cannot determine ChromeDriver version automatically. Please install it manually or rely on webdriver-manager."
  fi

  cd "$HOME/project/src"
else
  echo "...Using cached ChromeDriver"
fi