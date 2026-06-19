#!/usr/bin/env python3
"""Run focused reconstruction cases and generate Python/C++ comparison galleries."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
from typing import Any

import numpy as np
from PIL import Image, ImageDraw
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"

CASES = [
    {
        "name": "g-30x30-1",
        "signal_file": "data/g-30x30-1.csv",
        "model_file": "data/H-2.csv",
        "dimension": "30x30",
    },
    {
        "name": "g-30x30-2",
        "signal_file": "data/g-30x30-2.csv",
        "model_file": "data/H-2.csv",
        "dimension": "30x30",
    },
    {
        "name": "G-1",
        "signal_file": "data/G-1.csv",
        "model_file": "data/H-1.csv",
        "dimension": "60x60",
    },
    {
        "name": "G-2",
        "signal_file": "data/G-2.csv",
        "model_file": "data/H-1.csv",
        "dimension": "60x60",
    },
]

NO_GABARITO_CASES = [
    {
        "name": "A-30x30-1",
        "signal_file": "data/A-30x30-1.csv",
        "model_file": "data/H-2.csv",
        "dimension": "30x30",
    },
    {
        "name": "A-60x60-1",
        "signal_file": "data/A-60x60-1.csv",
        "model_file": "data/H-1.csv",
        "dimension": "60x60",
    },
]

CASE_GROUPS = {
    "gabarito": CASES,
    "sem-gabarito": NO_GABARITO_CASES,
    "todos": CASES + NO_GABARITO_CASES,
}


def post_reconstruction(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "ok":
        raise RuntimeError(f"Reconstrucao falhou em {url}: {data}")
    return data


def compare_csv(left: str, right: str) -> dict[str, float]:
    left_data = np.loadtxt(left, delimiter=",")
    right_data = np.loadtxt(right, delimiter=",")
    diff = np.abs(left_data - right_data)
    return {
        "max_abs_diff": float(np.max(diff)),
        "mean_abs_diff": float(np.mean(diff)),
    }


def result_link(path_text: str | None) -> str:
    if not path_text:
        return "-"
    path = Path(path_text)
    try:
        return path.resolve().relative_to(RESULTS_DIR).as_posix()
    except ValueError:
        return path.as_posix()


def image_cell(result: dict[str, Any]) -> str:
    outputs = result["outputs"]
    visual = result_link(outputs.get("png_visualization"))
    raw = result_link(outputs.get("png_raw") or outputs.get("png"))
    csv = result_link(outputs.get("csv"))
    metadata = result_link(result.get("metadata_file"))
    return (
        f'<img src="{visual}" width="260" alt="visual"><br>'
        f"[visual]({visual}) / [raw]({raw}) / [csv]({csv}) / [metadata]({metadata})<br>"
        f"iter={result['iterations']} / rec={result['reconstruction_time_seconds']:.6f}s / "
        f"residual={result['residual_norm_final']:.6g}"
    )


def report_title(group: str) -> str:
    if group == "sem-gabarito":
        return "Resultados Focados nos Casos Sem Gabarito"
    if group == "todos":
        return "Resultados Focados em Todos os Casos"
    return "Resultados Focados nos 4 Gabaritos"


def write_index(report: dict[str, Any], path: Path) -> None:
    lines = [
        f"# {report_title(report['case_group'])}",
        "",
        f"Gerado em `{report['started_at']}`.",
        "",
        "Arquivos-base mantidos somente leitura nesta rodada: `H-1.csv`, `H-2.csv`, "
        "`g-30x30-1.csv`, `g-30x30-2.csv`, `G-1.csv`, `G-2.csv`, "
        "`A-30x30-1.csv`, `A-60x60-1.csv`.",
        "",
        "| Caso | Modelo | Algoritmo | Python | C++ | Diferença Python vs C++ |",
        "|---|---|---|---|---|---|",
    ]
    for item in report["cases"]:
        comparison = item["comparison"]
        diff = (
            f"max={comparison['max_abs_diff']:.6g}<br>"
            f"mean={comparison['mean_abs_diff']:.6g}"
        )
        lines.append(
            "| "
            f"`{item['case']['signal_file']}` | "
            f"`{item['case']['model_file']}` | "
            f"`{item['payload']['algorithm'].upper()}` | "
            f"{image_cell(item['python'])} | "
            f"{image_cell(item['cpp'])} | "
            f"{diff} |"
        )
    lines.extend(
        [
            "",
            "Observacao: o aprimoramento aplicado aqui e visual. Os CSVs de entrada nao foram alterados; "
            "os CSVs de saida continuam registrando a reconstrucao numerica completa.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_gallery(report: dict[str, Any], path: Path) -> None:
    thumb_width = 420
    label_height = 28
    rows = []
    for item in report["cases"]:
        row = []
        for side in ("python", "cpp"):
            image_path = Path(item[side]["outputs"]["png_visualization"])
            image = Image.open(image_path).convert("RGB")
            thumb_height = int(image.height * thumb_width / image.width)
            image = image.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
            row.append((image, f"{item['case']['name']} {side}"))
        rows.append(row)

    row_height = max(max(cell[0].height for cell in row) for row in rows) + label_height
    canvas = Image.new("RGB", (thumb_width * 2, row_height * len(rows)), "white")
    draw = ImageDraw.Draw(canvas)
    for row_index, row in enumerate(rows):
        for col_index, (image, label) in enumerate(row):
            x = col_index * thumb_width
            y = row_index * row_height
            draw.text((x + 8, y + 6), label, fill="black")
            canvas.paste(image, (x, y + label_height))
    canvas.save(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python-url", default="http://localhost:8000/reconstruct")
    parser.add_argument("--cpp-url", default="http://localhost:8001/reconstruct")
    parser.add_argument("--timeout", type=float, default=240.0)
    parser.add_argument("--case-group", choices=sorted(CASE_GROUPS), default="gabarito")
    parser.add_argument("--output-json", type=Path, default=RESULTS_DIR / "gabarito_focus_results.json")
    parser.add_argument("--output-index", type=Path, default=RESULTS_DIR / "gabarito_focus_index.md")
    parser.add_argument("--output-gallery", type=Path, default=RESULTS_DIR / "gabarito_focus_gallery.png")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "case_group": args.case_group,
        "python_url": args.python_url,
        "cpp_url": args.cpp_url,
        "cases": [],
    }
    for case in CASE_GROUPS[args.case_group]:
        payload = {
            "signal_file": case["signal_file"],
            "model_file": case["model_file"],
            "apply_gain": True,
            "algorithm": "cgnr",
        }
        python_result = post_reconstruction(args.python_url, payload, args.timeout)
        cpp_result = post_reconstruction(args.cpp_url, payload, args.timeout)
        comparison = compare_csv(python_result["outputs"]["csv"], cpp_result["outputs"]["csv"])
        report["cases"].append(
            {
                "case": case,
                "payload": payload,
                "python": python_result,
                "cpp": cpp_result,
                "comparison": comparison,
            }
        )

    report["ended_at"] = datetime.now(timezone.utc).isoformat()
    args.output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_index(report, args.output_index)
    write_gallery(report, args.output_gallery)
    print(
        json.dumps(
            {
                "output_json": str(args.output_json),
                "output_index": str(args.output_index),
                "output_gallery": str(args.output_gallery),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
