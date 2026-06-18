#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [ -x "$ROOT/python_server/.venv/bin/python" ]; then
  PYTHON="$ROOT/python_server/.venv/bin/python"
else
  PYTHON="python3"
fi

"$PYTHON" -m py_compile python_server/cgnr.py python_server/image_utils.py python_server/blas_tests.py python_server/server.py client/client.py client/saturation_test.py reports/generate_report.py

cd "$ROOT/python_server"
"$PYTHON" blas_tests.py --size 128 --output "$ROOT/results/python_blas_report.json"

cd "$ROOT/cpp_server"
cmake -S . -B build
cmake --build build -j
./build/cpp_reconstruction_server --blas-tests "$ROOT/results/cpp_blas_report.json"

cd "$ROOT"
"$PYTHON" reports/generate_report.py
echo "Validação concluída."
