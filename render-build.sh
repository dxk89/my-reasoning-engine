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
# already present.  We use dpkg -x to unpack the .deb package into
# the directory because apt is not available in the native Render
# environment.
if [[ ! -d "$STORAGE_DIR/chrome" ]]; then
  echo "...Downloading Chrome"
  mkdir -p "$STORAGE_DIR/chrome"
  cd "$STORAGE_DIR/chrome"
  wget -P ./ https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  # Extract the .deb package without installing system‑wide
  dpkg -x ./google-chrome-stable_current_amd64.deb "$STORAGE_DIR/chrome"
  rm ./google-chrome-stable_current_amd64.deb
  cd "$HOME/project/src" || true
else
  echo "...Using Chrome from cache"
fi

# Note: you must add Chrome’s location to the PATH in the Start Command,
# e.g.: export PATH="${PATH}:/opt/render/project/.render/chrome/opt/google/chrome"
# before invoking your application.