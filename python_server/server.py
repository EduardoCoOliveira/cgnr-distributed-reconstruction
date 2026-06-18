"""FastAPI reconstruction service with saturation control."""

from __future__ import annotations

from pathlib import Path
import asyncio
import logging
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from cgnr import ReconstructionRequest, reconstruct, resolve_path

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
LOGGER = logging.getLogger("python_server")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT_RECONSTRUCTIONS", "2"))
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

app = FastAPI(title="Python CGNR Reconstruction Server", version="1.0.0")


class ReconstructPayload(BaseModel):
    """REST payload for image reconstruction."""

    signal_file: str
    model_file: str
    apply_gain: bool = True
    algorithm: str = Field(default="cgnr", pattern="^(cgnr|cgne)$")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "python", "max_concurrent": MAX_CONCURRENT}


@app.post("/reconstruct")
async def reconstruct_endpoint(payload: ReconstructPayload) -> dict:
    if semaphore.locked():
        raise HTTPException(status_code=429, detail={"status": "error", "error": "Servidor Python saturado"})

    await semaphore.acquire()
    try:
        request = ReconstructionRequest(
            signal_file=resolve_path(payload.signal_file, PROJECT_ROOT),
            model_file=resolve_path(payload.model_file, PROJECT_ROOT),
            apply_gain=payload.apply_gain,
            algorithm=payload.algorithm,  # type: ignore[arg-type]
            output_dir=PROJECT_ROOT / "results",
        )
        return await asyncio.to_thread(reconstruct, request)
    except FileNotFoundError as exc:
        LOGGER.exception("Arquivo ausente")
        raise HTTPException(status_code=404, detail={"status": "error", "error": str(exc)}) from exc
    except ValueError as exc:
        LOGGER.exception("Requisição inválida")
        raise HTTPException(status_code=400, detail={"status": "error", "error": str(exc)}) from exc
    except Exception as exc:
        LOGGER.exception("Falha interna na reconstrução")
        raise HTTPException(status_code=500, detail={"status": "error", "error": str(exc)}) from exc
    finally:
        semaphore.release()
