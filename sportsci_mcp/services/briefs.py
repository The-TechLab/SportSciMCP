from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from sportsci_mcp.config import briefs_dir
from sportsci_mcp.models import SearchRecord


def save_brief(
    record: SearchRecord,
    *,
    tags: list[str] | None = None,
    notes: str = "",
) -> dict:
    base = briefs_dir()
    base.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", record.title.lower())[:60].strip("-") or "brief"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    fname = f"{stamp}_{record.source}_{record.id}_{slug}.md"
    path = base / fname
    tag_line = ", ".join(tags or [])
    body = f"""# {record.title}

- **Ref:** `{record.ref}`
- **Source:** {record.source}
- **URL:** {record.url}
- **Year:** {record.year or "n/a"}
- **Journal:** {record.journal or "n/a"}
- **DOI:** {record.doi or "n/a"}
- **Tags:** {tag_line or "none"}
- **Saved:** {datetime.now(timezone.utc).isoformat()}

## Authors

{", ".join(record.authors) if record.authors else "n/a"}

## Abstract

{record.abstract or "_No abstract available._"}

## Notes

{notes or "_Add your synthesis here._"}
"""
    path.write_text(body, encoding="utf-8")
    return {
        "path": str(path),
        "preview": body[:500] + ("..." if len(body) > 500 else ""),
    }


def format_for_notebooklm(record: SearchRecord, *, notebook_alias: str = "") -> str:
    header = f"# Source: {record.title}\n\n"
    meta = (
        f"- Ref: `{record.ref}`\n"
        f"- URL: {record.url}\n"
        f"- Year: {record.year or 'n/a'}\n"
        f"- DOI: {record.doi or 'n/a'}\n\n"
    )
    authors = "## Authors\n\n" + (", ".join(record.authors) or "n/a") + "\n\n"
    abstract = "## Content\n\n" + (record.abstract or "_See linked source._")
    footer = ""
    if notebook_alias:
        footer = f"\n\n---\n_suggested notebook alias: `{notebook_alias}`_\n"
    return header + meta + authors + abstract + footer
