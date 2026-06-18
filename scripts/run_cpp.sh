#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../cpp_server"
cmake -S . -B build
cmake --build build -j
./build/cpp_reconstruction_server
