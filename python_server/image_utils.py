"""Image conversion utilities for reconstruction vectors."""

from __future__ import annotations

from pathlib import Path
import csv
import os

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt
import numpy as np


def infer_image_dimension(vector_size: int) -> int:
    """Infer supported square image dimension from vector length."""

    if vector_size == 900:
        return 30
    if vector_size == 3600:
        return 60
    root = int(np.sqrt(vector_size))
    if root * root == vector_size:
        return root
    raise ValueError(f"Tamanho de imagem não suportado: {vector_size}")


def normalize_to_uint8(image: np.ndarray) -> np.ndarray:
    """Normalize a floating-point image into 8-bit grayscale."""

    minimum = float(np.min(image))
    maximum = float(np.max(image))
    if maximum - minimum <= np.finfo(np.float64).eps:
        return np.zeros(image.shape, dtype=np.uint8)
    scaled = (image - minimum) / (maximum - minimum)
    return np.clip(scaled * 255.0, 0, 255).astype(np.uint8)


def vector_to_image(vector: np.ndarray, dimension: int) -> np.ndarray:
    """Convert the reconstruction vector using MATLAB-compatible column order."""

    return vector.reshape((dimension, dimension), order="F")


def save_visualization_png(image: np.ndarray, path: Path) -> None:
    """Save a report-style spot-map visualization with title and axes."""

    log_image = np.log1p(np.abs(image))
    spot_image = build_spot_map(log_image)
    fig, ax = plt.subplots(figsize=(4.2, 4.2), dpi=160)
    ax.imshow(spot_image, cmap="gray", origin="upper", vmin=0.0, vmax=1.0, interpolation="nearest")
    ax.set_title("Log")
    ticks = list(range(9, image.shape[0], 10))
    labels = [str(tick + 1) for tick in ticks]
    ax.set_xticks(ticks, labels)
    ax.set_yticks(ticks, labels)
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def build_spot_map(score: np.ndarray) -> np.ndarray:
    """Keep only strong local maxima so the visualization resembles the reference plot."""

    threshold = max(float(np.percentile(score, 97.4)), float(np.max(score)) * 0.30)
    candidates: list[tuple[float, int, int]] = []
    rows, cols = score.shape
    for row in range(rows):
        for col in range(cols):
            value = float(score[row, col])
            if value < threshold:
                continue
            row_start = max(0, row - 1)
            row_end = min(rows, row + 2)
            col_start = max(0, col - 1)
            col_end = min(cols, col + 2)
            if value >= float(np.max(score[row_start:row_end, col_start:col_end])):
                candidates.append((value, row, col))

    candidates.sort(reverse=True)
    max_spots = 72 if rows >= 60 else 30
    min_distance = 2
    selected: list[tuple[float, int, int]] = []
    for value, row, col in candidates:
        if all((row - sr) ** 2 + (col - sc) ** 2 >= min_distance**2 for _, sr, sc in selected):
            selected.append((value, row, col))
        if len(selected) >= max_spots:
            break

    spot_image = np.zeros_like(score, dtype=np.float64)
    if not selected:
        return spot_image

    selected_values = np.array([value for value, _, _ in selected], dtype=np.float64)
    min_value = float(np.min(selected_values))
    max_value = float(np.max(selected_values))
    for value, row, col in selected:
        if max_value - min_value <= np.finfo(np.float64).eps:
            intensity = 1.0
        else:
            intensity = 0.45 + 0.55 * ((value - min_value) / (max_value - min_value))
        spot_image[row, col] = max(spot_image[row, col], intensity)
        if rows >= 60:
            # A tiny 2-pixel footprint makes true reflectors visible after rendering.
            if row + 1 < rows:
                spot_image[row + 1, col] = max(spot_image[row + 1, col], intensity * 0.72)
            if col + 1 < cols:
                spot_image[row, col + 1] = max(spot_image[row, col + 1], intensity * 0.72)

    return spot_image


def save_image_outputs(vector: np.ndarray, output_dir: Path, base_name: str) -> dict:
    """Save reconstructed vector as oriented CSV, raw PNG and visualization PNG."""

    dimension = infer_image_dimension(vector.size)
    image = vector_to_image(vector, dimension)
    csv_path = output_dir / f"{base_name}.csv"
    png_raw_path = output_dir / f"{base_name}.png"
    png_visualization_path = output_dir / f"{base_name}_visualization.png"

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerows(image.tolist())

    plt.imsave(png_raw_path, normalize_to_uint8(image), cmap="gray")
    save_visualization_png(image, png_visualization_path)

    return {
        "dimension": f"{dimension}x{dimension}",
        "orientation": "column-major",
        "csv": str(csv_path),
        "png": str(png_raw_path),
        "png_raw": str(png_raw_path),
        "png_visualization": str(png_visualization_path),
    }
