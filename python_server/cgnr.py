"""Manual CGNR/CGNE reconstruction routines backed by NumPy/OpenBLAS."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Literal
import json
import logging
import os

import numpy as np
import pandas as pd
import psutil

from image_utils import save_image_outputs

Algorithm = Literal["cgnr", "cgne"]

LOGGER = logging.getLogger("python_server.cgnr")
EPSILON_THRESHOLD = 1e-4
MAX_ITERATIONS = 10


@dataclass(frozen=True)
class ReconstructionRequest:
    """Normalized reconstruction request used by the service and tests."""

    signal_file: Path
    model_file: Path
    apply_gain: bool = True
    algorithm: Algorithm = "cgnr"
    output_dir: Path = Path("../results")


def resolve_path(path: str | Path, base_dir: Path | None = None) -> Path:
    """Resolve absolute or project-relative paths consistently."""

    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    root = base_dir or Path(__file__).resolve().parents[1]
    return (root / candidate).resolve()


def load_matrix_csv(path: Path) -> np.ndarray:
    """Load a numeric CSV as a 2D float64 NumPy array."""

    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    data = pd.read_csv(path, header=None).to_numpy(dtype=np.float64)
    if data.ndim != 2:
        raise ValueError(f"CSV inválido para matriz: {path}")
    return np.ascontiguousarray(data)


def load_signal_csv(path: Path) -> np.ndarray:
    """Load a signal CSV as a contiguous 1D float64 vector."""

    data = load_matrix_csv(path)
    if 1 not in data.shape:
        raise ValueError(f"Sinal deve ter uma coluna ou linha: {path} shape={data.shape}")
    return np.ascontiguousarray(data.reshape(-1))


def apply_signal_gain(g: np.ndarray) -> np.ndarray:
    """Apply gamma_l = 100 + (1/20) * l * sqrt(l) to every signal sample."""

    # The assignment uses l as a 1-based sample index.
    indices = np.arange(1, g.size + 1, dtype=np.float64)
    gamma = 100.0 + 0.05 * indices * np.sqrt(indices)
    return np.ascontiguousarray(g * gamma)


def estimate_reduction_factor(H: np.ndarray, iterations: int = 12) -> float:
    """Estimate ||H^T H||_2 with power iteration."""

    n = H.shape[1]
    v = np.ones(n, dtype=np.float64)
    v /= np.linalg.norm(v)
    value = 0.0
    for _ in range(iterations):
        normal_v = H.T @ (H @ v)
        norm = float(np.linalg.norm(normal_v))
        if norm == 0.0:
            return 0.0
        v = normal_v / norm
        value = float(v @ (H.T @ (H @ v)))
    return value


def compute_regularization_lambda(H: np.ndarray, g: np.ndarray) -> float:
    """Compute lambda = max(abs(H^T g)) * 0.10."""

    htg = H.T @ g
    return float(np.max(np.abs(htg)) * 0.10)


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator <= np.finfo(np.float64).eps:
        return 0.0
    return numerator / denominator


def cgnr(H: np.ndarray, g: np.ndarray) -> tuple[np.ndarray, dict]:
    """Run the exact CGNR recurrence requested in the assignment."""

    f = np.zeros(H.shape[1], dtype=np.float64)
    r = np.ascontiguousarray(g - H @ f)
    z = np.ascontiguousarray(H.T @ r)
    p = z.copy()
    previous_norm = float(np.linalg.norm(r))
    epsilon = float("inf")
    iterations = 0

    for i in range(MAX_ITERATIONS):
        w = H @ p
        z_norm_sq = float(z @ z)
        alpha = _safe_divide(z_norm_sq, float(w @ w))
        f = f + alpha * p
        r_next = r - alpha * w
        current_norm = float(np.linalg.norm(r_next))
        epsilon = abs(current_norm - previous_norm)
        iterations = i + 1

        z_next = np.ascontiguousarray(H.T @ r_next)
        beta = _safe_divide(float(z_next @ z_next), z_norm_sq)
        p = z_next + beta * p
        r = np.ascontiguousarray(r_next)
        z = z_next
        previous_norm = current_norm

        if epsilon < EPSILON_THRESHOLD:
            break

    return f, {
        "iterations": iterations,
        "epsilon_final": float(epsilon),
        "residual_norm_final": float(np.linalg.norm(r)),
    }


def cgne(H: np.ndarray, g: np.ndarray) -> tuple[np.ndarray, dict]:
    """Run CGNE as an optional algorithm using the recurrence from the brief."""

    f = np.zeros(H.shape[1], dtype=np.float64)
    r = np.ascontiguousarray(g - H @ f)
    p = np.ascontiguousarray(H.T @ r)
    previous_norm = float(np.linalg.norm(r))
    epsilon = float("inf")
    iterations = 0

    for i in range(MAX_ITERATIONS):
        hp = H @ p
        r_norm_sq = float(r @ r)
        alpha = _safe_divide(r_norm_sq, float(p @ p))
        f = f + alpha * p
        r_next = r - alpha * hp
        current_norm = float(np.linalg.norm(r_next))
        epsilon = abs(current_norm - previous_norm)
        iterations = i + 1

        beta = _safe_divide(float(r_next @ r_next), r_norm_sq)
        p = (H.T @ r_next) + beta * p
        r = np.ascontiguousarray(r_next)
        previous_norm = current_norm

        if epsilon < EPSILON_THRESHOLD:
            break

    return f, {
        "iterations": iterations,
        "epsilon_final": float(epsilon),
        "residual_norm_final": float(np.linalg.norm(r)),
    }


def reconstruct(request: ReconstructionRequest) -> dict:
    """Load data, run reconstruction, write artifacts, and return metadata."""

    if request.algorithm not in ("cgnr", "cgne"):
        raise ValueError("algorithm deve ser 'cgnr' ou 'cgne'")

    process = psutil.Process(os.getpid())
    started_at = datetime.now(timezone.utc)
    wall_start = perf_counter()
    cpu_start = process.cpu_times()
    mem_start = process.memory_info().rss

    H = load_matrix_csv(request.model_file)
    g = load_signal_csv(request.signal_file)
    if H.shape[0] != g.size:
        raise ValueError(f"Dimensão incompatível: H={H.shape}, g={g.shape}")

    if request.apply_gain:
        g = apply_signal_gain(g)

    reduction_factor = estimate_reduction_factor(H)
    regularization_lambda = compute_regularization_lambda(H, g)

    reconstruction_start = perf_counter()
    if request.algorithm == "cgnr":
        f, stats = cgnr(H, g)
    else:
        f, stats = cgne(H, g)
    reconstruction_time = perf_counter() - reconstruction_start
    reconstruction_ended_at = datetime.now(timezone.utc)

    output_dir = request.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = started_at.strftime("%Y%m%dT%H%M%S%fZ")
    base_name = f"python_{request.algorithm}_{request.signal_file.stem}_{stamp}"
    image_info = save_image_outputs(
        f,
        output_dir,
        base_name,
        {
            "algorithm": request.algorithm.upper(),
            "started_at": started_at.isoformat(),
            "ended_at": reconstruction_ended_at.isoformat(),
            "iterations": stats["iterations"],
        },
    )

    ended_at = datetime.now(timezone.utc)
    total_time = perf_counter() - wall_start
    cpu_end = process.cpu_times()
    mem_end = process.memory_info().rss

    result = {
        "status": "ok",
        "service": "python",
        "algorithm": request.algorithm.upper(),
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "total_time_seconds": total_time,
        "reconstruction_time_seconds": reconstruction_time,
        "image_dimension": image_info["dimension"],
        "iterations": stats["iterations"],
        "epsilon_final": stats["epsilon_final"],
        "residual_norm_final": stats["residual_norm_final"],
        "memory_used_bytes": max(0, mem_end - mem_start),
        "memory_rss_bytes": mem_end,
        "cpu_user_seconds": cpu_end.user - cpu_start.user,
        "cpu_system_seconds": cpu_end.system - cpu_start.system,
        "cpu_percent": process.cpu_percent(interval=None),
        "apply_gain": request.apply_gain,
        "model_file": str(request.model_file),
        "signal_file": str(request.signal_file),
        "reduction_factor": reduction_factor,
        "regularization_lambda": regularization_lambda,
        "outputs": image_info,
    }

    metadata_path = output_dir / f"{base_name}_metadata.json"
    metadata_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    result["metadata_file"] = str(metadata_path)
    LOGGER.info("Reconstrução Python concluída: %s", metadata_path)
    return result
