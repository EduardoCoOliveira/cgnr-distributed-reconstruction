"""Client that sends the same reconstruction sequence to Python and C++ services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter, sleep
import argparse
import json
import random
import statistics
from typing import Any

import psutil
import requests


@dataclass(frozen=True)
class Target:
    name: str
    url: str


DEFAULT_TARGETS = [
    Target("python", "http://localhost:8000/reconstruct"),
    Target("cpp", "http://localhost:8001/reconstruct"),
]


def post_with_retry(url: str, payload: dict[str, Any], timeout: float, retries: int) -> dict[str, Any]:
    """POST with retry, timeout and standardized failure output."""

    last_error = "unknown error"
    for attempt in range(retries + 1):
        started = perf_counter()
        try:
            response = requests.post(url, json=payload, timeout=timeout)
            latency = perf_counter() - started
            if response.status_code == 200:
                data = response.json()
                data["client_latency_seconds"] = latency
                data["http_status"] = response.status_code
                return data
            last_error = f"HTTP {response.status_code}: {response.text}"
        except requests.RequestException as exc:
            last_error = str(exc)
        if attempt < retries:
            sleep(0.5 * (attempt + 1))
    return {
        "status": "error",
        "error": last_error,
        "client_latency_seconds": None,
        "http_status": None,
    }


def run_client(
    signal_files: list[str],
    model_file: str,
    targets: list[Target],
    requests_count: int,
    output: Path,
    timeout: float,
    retries: int,
) -> dict[str, Any]:
    """Send random interval requests to both services using the same payloads."""

    process = psutil.Process()
    started_at = datetime.now(timezone.utc)
    sequence = []
    for index in range(requests_count):
        sequence.append(
            {
                "signal_file": signal_files[index % len(signal_files)],
                "model_file": model_file,
                "apply_gain": random.choice([True, False]),
                "algorithm": random.choice(["cgnr", "cgne"]),
            }
        )

    results = []
    for payload in sequence:
        interval = random.uniform(1.0, 5.0)
        sleep(interval)
        for target in targets:
            sent_at = datetime.now(timezone.utc).isoformat()
            response = post_with_retry(target.url, payload, timeout, retries)
            results.append(
                {
                    "target": target.name,
                    "url": target.url,
                    "sent_at": sent_at,
                    "interval_seconds": interval,
                    "payload": payload,
                    "response": response,
                }
            )

    latencies = [
        item["response"]["client_latency_seconds"]
        for item in results
        if item["response"].get("client_latency_seconds") is not None
    ]
    report = {
        "started_at": started_at.isoformat(),
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "requests_count": requests_count,
        "targets": [target.__dict__ for target in targets],
        "memory_rss_bytes": process.memory_info().rss,
        "cpu_percent": process.cpu_percent(interval=None),
        "latency_average_seconds": statistics.mean(latencies) if latencies else None,
        "latency_max_seconds": max(latencies) if latencies else None,
        "results": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--signals", nargs="+", default=["data/G-1.csv", "data/G-2.csv"])
    parser.add_argument("--model", default="data/H-1.csv")
    parser.add_argument("--requests", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--output", type=Path, default=Path("../results/client_comparison.json"))
    parser.add_argument("--python-url", default="http://localhost:8000/reconstruct")
    parser.add_argument("--cpp-url", default="http://localhost:8001/reconstruct")
    args = parser.parse_args()
    targets = [Target("python", args.python_url), Target("cpp", args.cpp_url)]
    report = run_client(args.signals, args.model, targets, args.requests, args.output, args.timeout, args.retries)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
