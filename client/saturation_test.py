"""Concurrent saturation tests for Python and C++ reconstruction services."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
import argparse
import json
import statistics
from typing import Any

import psutil
import requests


LEVELS = [1, 2, 4, 8, 16, 32]


def one_request(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    started = perf_counter()
    try:
        response = requests.post(url, json=payload, timeout=timeout)
        return {
            "ok": response.status_code == 200,
            "status_code": response.status_code,
            "latency_seconds": perf_counter() - started,
            "error": None if response.status_code == 200 else response.text,
        }
    except requests.RequestException as exc:
        return {
            "ok": False,
            "status_code": None,
            "latency_seconds": perf_counter() - started,
            "error": str(exc),
        }


def run_level(url: str, payload: dict[str, Any], concurrency: int, timeout: float) -> dict[str, Any]:
    process = psutil.Process()
    started = perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(one_request, url, payload, timeout) for _ in range(concurrency)]
        responses = [future.result() for future in as_completed(futures)]
    elapsed = perf_counter() - started
    latencies = [item["latency_seconds"] for item in responses]
    errors = [item for item in responses if not item["ok"]]
    return {
        "concurrency": concurrency,
        "elapsed_seconds": elapsed,
        "average_time_seconds": statistics.mean(latencies) if latencies else 0.0,
        "max_time_seconds": max(latencies) if latencies else 0.0,
        "throughput_requests_per_second": concurrency / elapsed if elapsed > 0 else 0.0,
        "cpu_percent": process.cpu_percent(interval=None),
        "memory_rss_bytes": process.memory_info().rss,
        "errors": len(errors),
        "responses": responses,
    }


def run_saturation(url: str, payload: dict[str, Any], output: Path, timeout: float) -> dict[str, Any]:
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "url": url,
        "payload": payload,
        "levels": [run_level(url, payload, level, timeout) for level in LEVELS],
        "ended_at": datetime.now(timezone.utc).isoformat(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000/reconstruct")
    parser.add_argument("--signal", default="data/G-1.csv")
    parser.add_argument("--model", default="data/H-1.csv")
    parser.add_argument("--algorithm", default="cgnr", choices=["cgnr", "cgne"])
    parser.add_argument("--apply-gain", action="store_true")
    parser.add_argument("--timeout", type=float, default=240.0)
    parser.add_argument("--output", type=Path, default=Path("../results/saturation_report.json"))
    args = parser.parse_args()
    payload = {
        "signal_file": args.signal,
        "model_file": args.model,
        "apply_gain": args.apply_gain,
        "algorithm": args.algorithm,
    }
    print(json.dumps(run_saturation(args.url, payload, args.output, args.timeout), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
