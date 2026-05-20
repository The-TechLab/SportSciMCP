from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sportsci_mcp.config import data_dir


def rtp_checklist(injury: str, phase: str = "return_to_play") -> dict[str, Any]:
    slug = injury.strip().lower().replace(" ", "_")
    path = data_dir() / "rtp" / f"{slug}.yaml"
    if not path.exists():
        available = [p.stem for p in (data_dir() / "rtp").glob("*.yaml")]
        raise ValueError(
            f"No RTP checklist for '{injury}'. Available: {', '.join(sorted(available))}"
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    phases = data.get("phases") or {}
    if phase not in phases:
        raise ValueError(
            f"Unknown phase '{phase}' for {injury}. "
            f"Available: {', '.join(phases.keys())}"
        )
    return {
        "injury": data.get("injury", slug),
        "phase": phase,
        "title": phases[phase].get("title", phase),
        "criteria": phases[phase].get("criteria", []),
        "notes": data.get("notes", ""),
        "references": data.get("references", []),
    }
