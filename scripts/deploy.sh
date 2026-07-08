#!/usr/bin/env bash
# Deploy the Databricks Asset Bundle to the given target (default: dev).
set -euo pipefail
TARGET="${1:-dev}"
bash scripts/export_requirements.sh
databricks bundle validate -t "$TARGET"
databricks bundle deploy -t "$TARGET"
echo "Deployed bundle to target: $TARGET"
