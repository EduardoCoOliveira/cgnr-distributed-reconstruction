#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
if [ -x "python_server/.venv/bin/python" ]; then
  PYTHON="python_server/.venv/bin/python"
else
  PYTHON="python3"
fi
"$PYTHON" reports/generate_report.py
