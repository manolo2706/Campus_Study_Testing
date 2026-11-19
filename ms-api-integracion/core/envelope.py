from datetime import datetime, timezone
from typing import Any

from core.context import get_request_id


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_meta(request_id: str | None = None, warnings: list[dict[str, Any]] | None = None) -> dict:
    meta: dict[str, Any] = {
        "request_id": request_id or get_request_id(),
        "timestamp": _timestamp(),
    }
    if warnings:
        meta["warnings"] = warnings
    return meta


def ok(data: Any = None, warnings: list[dict[str, Any]] | None = None, request_id: str | None = None) -> dict:
    return {"data": data, "error": None, "meta": build_meta(request_id, warnings)}


def build_error(
    codigo: int,
    mensaje: str,
    detalle: str | None = None,
    request_id: str | None = None,
) -> dict:
    return {
        "data": None,
        "error": {"codigo": codigo, "mensaje": mensaje, "detalle": detalle},
        "meta": build_meta(request_id),
    }
