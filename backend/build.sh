#!/usr/bin/env bash
# build.sh

set -e

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers (Chromium, Firefox, WebKit)
python -m playwright install --with-deps