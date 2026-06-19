"""Medições de operações apoiadas por BLAS para a implementação Python."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
import argparse
import json
import os

import numpy as np
import psutil


def _measure(name: str, operation):
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss
    cpu_before = process.cpu_times()
    started = perf_counter()
    result = operation()
    elapsed = perf_counter() - started
    cpu_after = process.cpu_times()
    mem_after = process.memory_info().rss
    return {
        "operation": name,
        "time_seconds": elapsed,
        "result_shape": list(result.shape) if hasattr(result, "shape") else [],
        "memory_used_bytes": max(0, mem_after - mem_before),
        "memory_rss_bytes": mem_after,
        "cpu_user_seconds": cpu_after.user - cpu_before.user,
        "cpu_system_seconds": cpu_after.system - cpu_before.system,
    }


def run_blas_tests(size: int = 512, output: Path = Path("../results/python_blas_report.json")) -> dict:
    """Executa operações MN, aM e Ma pela integração BLAS do NumPy."""

    rng = np.random.default_rng(42)
    M = np.ascontiguousarray(rng.normal(size=(size, size)))
    N = np.ascontiguousarray(rng.normal(size=(size, size)))
    vector = np.ascontiguousarray(rng.normal(size=size))
    scalar = 2.5

    results = [
        _measure("MN = M * N", lambda: M @ N),
        _measure("aM = a * M (scalar)", lambda: scalar * M),
        _measure("aM = a * M (vector left)", lambda: vector @ M),
        _measure("Ma = M * a (scalar)", lambda: M * scalar),
        _measure("Ma = M * a (vector right)", lambda: M @ vector),
    ]
    report = {
        "service": "python",
        "blas_backend": str(np.__config__.show(mode="dicts")),
        "matrix_size": size,
        "results": results,
    }
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--output", type=Path, default=Path("../results/python_blas_report.json"))
    args = parser.parse_args()
    print(json.dumps(run_blas_tests(args.size, args.output), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
