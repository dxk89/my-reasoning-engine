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

# Download and extract Chrome into the storage directory if it’s not
# already present. Instead of unpacking a Debian package via dpkg (which
# occasionally fails in constrained environments), we fetch the
# "Chrome for Testing" zip archive directly from Google. This archive
# contains a portable, headless Chrome binary that doesn’t require
# installation.  After extraction, the binary will live under
# "$STORAGE_DIR/chrome/chrome-linux64/chrome".
if [[ ! -d "$STORAGE_DIR/chrome/chrome-linux64" && ! -d "$STORAGE_DIR/chrome/opt/google/chrome" ]]; then
  echo "...Installing Chrome"
  mkdir -p "$STORAGE_DIR/chrome"
  cd "$STORAGE_DIR/chrome"
  # First try to download Chrome for Testing (zip).  If this fails,
  # fallback to the .deb package.  Either method will exit on failure
  # because of 'set -o errexit'.
  set +o errexit
  # Download a specific stable version of Chrome for Testing.  See
  # https://googlechromelabs.github.io/chrome-for-testing/ for the
  # latest available versions.  We pin to version 140.0.7339.185 for
  # stability.  If this download fails, we fall back to installing
  # from the .deb package.
  wget -q -O chrome-linux64.zip \
    https://storage.googleapis.com/chrome-for-testing-public/140.0.7339.185/linux64/chrome-linux64.zip
  if [[ $? -eq 0 ]]; then
    echo "...Extracting Chrome for Testing"
    unzip -q chrome-linux64.zip
    rm chrome-linux64.zip
    set -o errexit
  else
    echo "...Failed to download Chrome for Testing. Falling back to .deb installation"
    rm -f chrome-linux64.zip
    set -o errexit
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    # Extract the .deb package without installing system‑wide.  The
    # binary will end up under opt/google/chrome/google-chrome.
    # Extract the .deb package without using dpkg -x (which can fail with EOF
    # errors on some systems).  We use ar to extract the data archive, then
    # untar it into the storage directory.  This creates
    # $STORAGE_DIR/chrome/opt/google/chrome/google-chrome.
    ar x google-chrome-stable_current_amd64.deb
    tar -xf data.tar.* -C "$STORAGE_DIR/chrome"
    # Clean up temporary files
    rm google-chrome-stable_current_amd64.deb control.tar.* data.tar.* debian-binary
  fi
  cd "$HOME/project/src" || true
else
  echo "...Using cached Chrome"
fi

# Note: you must add Chrome’s location to the PATH in the Start Command.
# For example:
#   export GOOGLE_CHROME_BIN="/opt/render/project/.render/chrome/chrome-linux64/chrome"
#   export PATH="$PATH:/opt/render/project/.render/chrome/chrome-linux64"