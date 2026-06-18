# CGNR Distributed Reconstruction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete academic client-server image reconstruction project with Python and C++ CGNR/CGNE implementations.

**Architecture:** The project has two independent reconstruction services with equivalent REST APIs, a shared Python client, automated BLAS/reconstruction/saturation reports, and repository documentation for continuity. Python uses FastAPI/NumPy/OpenBLAS; C++ uses C++17, CBLAS/OpenBLAS, CMake, and a small built-in HTTP server.

**Tech Stack:** Python 3.12+, FastAPI, Uvicorn, NumPy, Pandas, Matplotlib, psutil, requests; C++17, OpenBLAS/CBLAS, CMake, POSIX sockets, zlib-free minimal PNG encoding.

---

### Task 1: Project Structure and Context

**Files:**
- Create directories: `data/`, `python_server/`, `cpp_server/`, `client/`, `reports/`, `results/`, `docs/`, `scripts/`
- Create docs: `docs/ai-context.md`, `docs/session-log.md`, `docs/next-step.md`, `docs/decisions.md`

- [x] Create the required project tree.
- [x] Record environment as Mac and mode as executor.
- [x] Document missing 30x30 files and available 60x60 files.

### Task 2: Python Reconstruction Service

**Files:**
- Create: `python_server/cgnr.py`
- Create: `python_server/image_utils.py`
- Create: `python_server/blas_tests.py`
- Create: `python_server/server.py`
- Create: `python_server/requirements.txt`
- Create: `python_server/README.md`

- [x] Implement CSV loading, signal gain, factor computations, CGNR, optional CGNE, image CSV/PNG output, metrics JSON.
- [x] Implement BLAS benchmark using NumPy operations backed by BLAS.
- [x] Implement FastAPI endpoint `POST /reconstruct` with semaphore saturation control and standardized error responses.

### Task 3: C++ Reconstruction Service

**Files:**
- Create: `cpp_server/cgnr.hpp`
- Create: `cpp_server/cgnr.cpp`
- Create: `cpp_server/blas_tests.cpp`
- Create: `cpp_server/main.cpp`
- Create: `cpp_server/CMakeLists.txt`
- Create: `cpp_server/README.md`

- [x] Implement CBLAS matrix-vector operations and manual CGNR/CGNE logic.
- [x] Implement CSV/PNG/JSON output without automatic CG solvers.
- [x] Implement minimal HTTP service with `POST /reconstruct`, timeout-safe parsing, and 429 saturation response.

### Task 4: Client, Saturation and Automation

**Files:**
- Create: `client/client.py`
- Create: `client/saturation_test.py`
- Create: `client/README.md`
- Create: `scripts/run_python.sh`
- Create: `scripts/run_cpp.sh`
- Create: `scripts/run_all_tests.sh`
- Create: `scripts/generate_report.sh`
- Create: `docker-compose.yml`

- [x] Implement retry, timeout, unavailable-server handling, shared request sequence for both services, and comparative report JSON.
- [x] Implement concurrent saturation levels 1, 2, 4, 8, 16, 32.
- [x] Add scripts and Docker Compose.

### Task 5: Report and Validation

**Files:**
- Create: `reports/generate_report.py`
- Create/update: `reports/report.md`

- [x] Generate a report with project requirements, BLAS, CGNR/CGNE, saturation, and distributed systems concepts.
- [ ] Run syntax checks.
- [ ] Run CMake configuration when dependencies are available.
