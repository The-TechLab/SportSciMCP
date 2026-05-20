from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sportsci_mcp.config import data_dir


def _norms_path() -> Path:
    return data_dir() / "norms.yaml"


def lookup_norms(
    metric: str,
    *,
    sex: str | None = None,
    sport: str | None = None,
    level: str | None = None,
) -> dict[str, Any]:
    path = _norms_path()
    if not path.exists():
        raise FileNotFoundError(f"Norms database not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    metrics = data.get("metrics") or {}
    key = metric.strip().lower().replace(" ", "_")
    if key not in metrics:
        available = sorted(metrics.keys())
        raise ValueError(f"Unknown metric '{metric}'. Available: {', '.join(available)}")
    entry = metrics[key]
    matches = []
    for row in entry.get("values", []):
        if sex and row.get("sex", "").lower() != sex.lower():
            continue
        if sport and sport.lower() not in str(row.get("sport", "")).lower():
            continue
        if level and level.lower() not in str(row.get("level", "")).lower():
            continue
        matches.append(row)
    if not matches:
        matches = entry.get("values", [])
    return {
        "metric": key,
        "description": entry.get("description", ""),
        "unit": entry.get("unit", ""),
        "matches": matches,
        "source": entry.get("source", "curated — verify before clinical use"),
    }
