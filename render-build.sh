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
if [[ ! -d "$STORAGE_DIR/chrome/chrome-linux64" ]]; then
  echo "...Downloading Chrome for Testing"
  mkdir -p "$STORAGE_DIR/chrome"
  cd "$STORAGE_DIR/chrome"
  # Fetch the latest Chrome for Testing release; see
  # https://developer.chrome.com/docs/chrome-for-testing
  # We use a direct download of the latest linux64 archive. If this
  # fails for any reason (e.g. network issues), the build will exit
  # immediately due to 'set -o errexit'.
  wget -q -O chrome-linux64.zip \
    https://storage.googleapis.com/chrome-for-testing-public/latest/linux64/chrome-linux64.zip
  unzip -q chrome-linux64.zip
  rm chrome-linux64.zip
  cd "$HOME/project/src" || true
else
  echo "...Using cached Chrome"
fi

# Note: you must add Chrome’s location to the PATH in the Start Command.
# For example:
#   export GOOGLE_CHROME_BIN="/opt/render/project/.render/chrome/chrome-linux64/chrome"
#   export PATH="$PATH:/opt/render/project/.render/chrome/chrome-linux64"