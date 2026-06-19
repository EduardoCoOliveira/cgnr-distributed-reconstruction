"""Utilitários de conversão de imagem para vetores reconstruídos."""

from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import matplotlib.pyplot as plt

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import csv
import os

os.environ.setdefault("MPLBACKEND", "Agg")

DISPLAY_TIMEZONE = os.getenv("DISPLAY_TIMEZONE", "America/Sao_Paulo")


def infer_image_dimension(vector_size: int) -> int:
    """Infere a dimensão quadrada suportada a partir do tamanho do vetor."""

    if vector_size == 900:
        return 30
    if vector_size == 3600:
        return 60
    root = int(np.sqrt(vector_size))
    if root * root == vector_size:
        return root
    raise ValueError(f"Tamanho de imagem não suportado: {vector_size}")


def normalize_to_uint8(image: np.ndarray) -> np.ndarray:
    """Normaliza uma imagem de ponto flutuante para tons de cinza de 8 bits."""

    minimum = float(np.min(image))
    maximum = float(np.max(image))
    if maximum - minimum <= np.finfo(np.float64).eps:
        return np.zeros(image.shape, dtype=np.uint8)
    scaled = (image - minimum) / (maximum - minimum)
    return np.clip(scaled * 255.0, 0, 255).astype(np.uint8)


def vector_to_image(vector: np.ndarray, dimension: int) -> np.ndarray:
    """Converte o vetor reconstruído usando ordem por coluna compatível com MATLAB."""

    return vector.reshape((dimension, dimension), order="F")


def format_display_time(value: object) -> str:
    """Formata datas ISO para os rótulos da visualização gerada."""

    if not value:
        return "-"
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        parsed = parsed.astimezone(ZoneInfo(DISPLAY_TIMEZONE))
        return parsed.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return text.replace("T", " ").split(".")[0].replace("+00:00", "")


def save_visualization_png(image: np.ndarray, path: Path, metadata: dict | None = None) -> None:
    """Salva a imagem reconstruída bruta com um painel de metadados."""

    scale = 2
    raw = Image.fromarray(normalize_to_uint8(image), mode="L").convert("RGB")
    preview = raw.resize((raw.width * scale, raw.height *
                         scale), Image.Resampling.NEAREST)
    font = ImageFont.load_default()
    algorithm = metadata.get("algorithm", "IMG") if metadata else "IMG"
    dimension = metadata.get(
        "dimension", f"{image.shape[0]}x{image.shape[1]}") if metadata else f"{image.shape[0]}x{image.shape[1]}"
    lines = [
        f"Algoritmo: {algorithm}",
        f"Inicio: {format_display_time(metadata.get('started_at')) if metadata else '-'}",
        f"Fim: {format_display_time(metadata.get('ended_at')) if metadata else '-'}",
        f"Pixels: {dimension}",
        f"Iteracoes: {metadata.get('iterations', '-') if metadata else '-'}",
    ]
    text_width = max(int(font.getlength(line)) for line in lines)
    line_height = 14
    padding = 8
    width = preview.width + text_width + padding * 3
    height = max(preview.height, line_height * len(lines) + padding * 2)
    canvas = Image.new("RGB", (width, height), "white")
    canvas.paste(preview, (padding, padding))
    draw = ImageDraw.Draw(canvas)
    x = preview.width + padding * 2
    y = padding
    for line in lines:
        draw.text((x, y), line, fill="black", font=font)
        y += line_height
    canvas.save(path)


def box_blur(image: np.ndarray, radius: int) -> np.ndarray:
    """Retorna um desfoque simples com borda refletida para imagens pequenas."""

    if radius <= 0:
        return image.copy()
    padded = np.pad(image, radius, mode="reflect")
    blurred = np.empty_like(image, dtype=np.float64)
    diameter = radius * 2 + 1
    area = float(diameter * diameter)
    for row in range(image.shape[0]):
        for col in range(image.shape[1]):
            window = padded[row: row + diameter, col: col + diameter]
            blurred[row, col] = float(np.sum(window) / area)
    return blurred


def median_filter(image: np.ndarray, radius: int) -> np.ndarray:
    """Retorna um filtro de mediana com borda refletida para imagens pequenas."""

    if radius <= 0:
        return image.copy()
    padded = np.pad(image, radius, mode="reflect")
    filtered = np.empty_like(image, dtype=np.float64)
    diameter = radius * 2 + 1
    for row in range(image.shape[0]):
        for col in range(image.shape[1]):
            window = padded[row: row + diameter, col: col + diameter]
            filtered[row, col] = float(np.median(window))
    return filtered


def normalize_log_display(score: np.ndarray) -> np.ndarray:
    """Normaliza uma imagem positiva usando contraste robusto por percentil alto."""

    positive = score[score > np.finfo(np.float64).eps]
    if positive.size == 0:
        return np.zeros_like(score, dtype=np.float64)
    upper = float(np.percentile(positive, 99.5))
    if upper <= np.finfo(np.float64).eps:
        upper = float(np.max(positive))
    if upper <= np.finfo(np.float64).eps:
        return np.zeros_like(score, dtype=np.float64)
    normalized = np.clip(score / upper, 0.0, 1.0)
    return np.power(normalized, 1.55)


def build_display_image(image: np.ndarray) -> np.ndarray:
    """Monta uma visualização com pontos quadrados preservando contexto fraco."""

    log_image = np.log1p(np.abs(image))
    log_image = 0.65 * median_filter(log_image, 1) + 0.35 * log_image
    radius = 2 if image.shape[0] <= 30 else 3
    background = box_blur(log_image, radius)
    local_detail = np.maximum(log_image - background, 0.0)
    enhanced = box_blur(local_detail, 1) + 0.06 * log_image
    context = normalize_log_display(enhanced) * 0.22
    points = build_square_point_map(log_image)
    return np.maximum(context, points)


def build_square_point_map(score: np.ndarray) -> np.ndarray:
    """Renderiza máximos locais fortes como marcadores quadrados nítidos."""

    max_score = float(np.max(score))
    if max_score <= np.finfo(np.float64).eps:
        return np.zeros_like(score, dtype=np.float64)

    threshold = max(float(np.percentile(score, 98.2)), max_score * 0.86)
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
    max_spots = 72 if rows >= 60 else 14
    min_distance = 3 if rows >= 60 else 2
    selected: list[tuple[float, int, int]] = []
    for value, row, col in candidates:
        if all((row - sr) ** 2 + (col - sc) ** 2 >= min_distance**2 for _, sr, sc in selected):
            selected.append((value, row, col))
        if len(selected) >= max_spots:
            break

    point_image = np.zeros_like(score, dtype=np.float64)
    if not selected:
        return point_image

    selected_values = np.array(
        [value for value, _, _ in selected], dtype=np.float64)
    low = float(np.min(selected_values))
    high = float(np.max(selected_values))
    half_size = 1 if rows >= 60 else 0
    for value, row, col in selected:
        if high - low <= np.finfo(np.float64).eps:
            intensity = 1.0
        else:
            intensity = 0.62 + 0.38 * ((value - low) / (high - low))
        for rr in range(max(0, row - half_size), min(rows, row + half_size + 1)):
            for cc in range(max(0, col - half_size), min(cols, col + half_size + 1)):
                point_image[rr, cc] = max(point_image[rr, cc], intensity)
    return point_image


def build_spot_map(score: np.ndarray) -> np.ndarray:
    """Mantém apenas máximos locais fortes para aproximar a visualização da referência."""

    max_score = float(np.max(score))
    if max_score <= np.finfo(np.float64).eps:
        return np.zeros_like(score, dtype=np.float64)

    threshold = max(float(np.percentile(score, 97.4)), max_score * 0.93)
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
    max_spots = 48 if rows >= 60 else 8
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

    selected_values = np.array(
        [value for value, _, _ in selected], dtype=np.float64)
    min_value = float(np.min(selected_values))
    max_value = float(np.max(selected_values))
    for value, row, col in selected:
        if max_value - min_value <= np.finfo(np.float64).eps:
            intensity = 1.0
        else:
            intensity = 0.45 + 0.55 * \
                ((value - min_value) / (max_value - min_value))
        spot_image[row, col] = max(spot_image[row, col], intensity)
        if rows >= 60:
            # Uma pequena marca de 2 pixels deixa refletores reais visíveis após a renderização.
            if row + 1 < rows:
                spot_image[row + 1,
                           col] = max(spot_image[row + 1, col], intensity * 0.72)
            if col + 1 < cols:
                spot_image[row, col +
                           1] = max(spot_image[row, col + 1], intensity * 0.72)

    return spot_image


def save_image_outputs(vector: np.ndarray, output_dir: Path, base_name: str, metadata: dict | None = None) -> dict:
    """Salva o vetor reconstruído como CSV orientado, PNG bruto e PNG de visualização."""

    dimension = infer_image_dimension(vector.size)
    image = vector_to_image(vector, dimension)
    csv_path = output_dir / f"{base_name}.csv"
    png_raw_path = output_dir / f"{base_name}.png"
    png_visualization_path = output_dir / f"{base_name}_visualization.png"

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerows(image.tolist())

    plt.imsave(png_raw_path, normalize_to_uint8(image), cmap="gray")
    visualization_metadata = dict(metadata or {})
    visualization_metadata.setdefault("dimension", f"{dimension}x{dimension}")
    save_visualization_png(image, png_visualization_path,
                           visualization_metadata)

    return {
        "dimension": f"{dimension}x{dimension}",
        "orientation": "column-major",
        "csv": str(csv_path),
        "png": str(png_raw_path),
        "png_raw": str(png_raw_path),
        "png_visualization": str(png_visualization_path),
    }
