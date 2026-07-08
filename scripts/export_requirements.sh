#!/usr/bin/env bash
# Regenerate requirements.txt from the uv lock for Databricks Apps.
set -euo pipefail
uv export --no-dev --format requirements-txt > requirements.txt
echo "Wrote requirements.txt"
