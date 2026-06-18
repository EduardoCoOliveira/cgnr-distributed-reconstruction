#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../python_server"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$(pwd)/../.matplotlib-cache}"
export MPLBACKEND="${MPLBACKEND:-Agg}"
if [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python3"
fi
"$PYTHON" -m uvicorn server:app --host 0.0.0.0 --port "${PYTHON_SERVER_PORT:-8000}"
