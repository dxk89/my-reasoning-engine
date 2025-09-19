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
# "Chrome for Testing" zip archive directly from a GitHub release in the
# user's repository. This archive contains a portable, headless Chrome
# binary that doesn’t require installation.  After extraction, the binary
# will live under "$STORAGE_DIR/chrome/chrome-linux64/chrome".  We also
# download a matching ChromeDriver archive from the same release and
# unpack it into "$STORAGE_DIR/chromedriver".  Having both the browser
# and its driver pre-installed avoids runtime network downloads and
# ensures the versions match, preventing "session not created" errors.
if [[ ! -d "$STORAGE_DIR/chrome/chrome-linux64" && ! -d "$STORAGE_DIR/chrome/opt/google/chrome" ]]; then
  echo "...Installing Chrome"
  mkdir -p "$STORAGE_DIR/chrome"
  cd "$STORAGE_DIR/chrome"
  # Temporarily disable errexit so we can handle download failures.
  set +o errexit
  # Try to download the Chrome archive from a GitHub release.  The user
  # should upload chrome-linux64.zip as a release asset.  If this
  # download succeeds, extract it.  Otherwise, fall back to the .deb
  # package.  Note: we use -L with wget to follow redirects.
  wget -q -O chrome-linux64.zip \
    https://github.com/dxk89/my-reasoning-engine/releases/download/v1.0/chrome-linux64.zip
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
    # Extract the .deb package without installing system‑wide.  Use ar
    # and tar to avoid dpkg -x which can fail with EOF errors.  The
    # binary will end up under opt/google/chrome/google-chrome.
    ar x google-chrome-stable_current_amd64.deb
    tar -xf data.tar.* -C "$STORAGE_DIR/chrome"
    # Clean up temporary files
    rm google-chrome-stable_current_amd64.deb control.tar.* data.tar.* debian-binary
  fi
  cd "$HOME/project/src" || true
else
  echo "...Using cached Chrome"
fi

# ------------------------------------------------------------------------------
# Install ChromeDriver into persistent storage.  The driver version must
# match the installed Chrome’s major version.  We assume that the user has
# uploaded a matching chromedriver-linux64.zip file to the same GitHub
# release.  The archive typically extracts into a directory named
# chromedriver-linux64 containing a single executable named chromedriver.
# Extract this driver into $STORAGE_DIR/chromedriver so it can be found at
# runtime.  If the driver is already present, skip downloading.
# ------------------------------------------------------------------------------
if [[ ! -f "$STORAGE_DIR/chromedriver/chromedriver" ]]; then
  echo "...Installing ChromeDriver"
  mkdir -p "$STORAGE_DIR/chromedriver"
  cd "$STORAGE_DIR/chromedriver"
  set +o errexit
  # Download the driver from the GitHub release.  The user must upload
  # chromedriver-linux64.zip as a release asset.  If this fails, the
  # build will exit with an error.  The -L option follows redirects.
  wget -q -O chromedriver-linux64.zip \
    https://github.com/dxk89/my-reasoning-engine/releases/download/v2.0/chromedriver-linux64.zip
  if [[ $? -eq 0 ]]; then
    echo "...Extracting ChromeDriver"
    unzip -q chromedriver-linux64.zip
    # Move the driver to the current directory (so its path is
    # $STORAGE_DIR/chromedriver/chromedriver)
    if [[ -f chromedriver-linux64/chromedriver ]]; then
      mv chromedriver-linux64/chromedriver .
    fi
    # Remove temporary files and directories
    rm -rf chromedriver-linux64 chromedriver-linux64.zip
    set -o errexit
  else
    echo "...ChromeDriver archive not found.  Proceeding without preinstalled driver."
    rm -f chromedriver-linux64.zip
    # Do not abort the build if driver cannot be downloaded.  The
    # application will fall back to downloading a driver at runtime via
    # webdriver_manager.
  fi
  cd "$HOME/project/src" || true
else
  echo "...Using cached ChromeDriver"
fi

# Note: you must add Chrome’s location to the PATH in the Start Command.
# For example:
#   export GOOGLE_CHROME_BIN="/opt/render/project/.render/chrome/chrome-linux64/chrome"
#   export PATH="$PATH:/opt/render/project/.render/chrome/chrome-linux64"