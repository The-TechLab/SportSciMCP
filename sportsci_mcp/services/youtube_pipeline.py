from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from sportsci_mcp.models import SearchRecord
from sportsci_mcp.services.briefs import save_brief
from sportsci_mcp.services import notebooklm as nlm

# Sibling TranscriptMCP repo (override with TRANSCRIPT_MCP_PATH)
_DEFAULT_TRANSCRIPT = Path(__file__).resolve().parents[2].parent / "TranscriptMCP"


def _ensure_transcript_import():
    root = Path(os.environ.get("TRANSCRIPT_MCP_PATH", str(_DEFAULT_TRANSCRIPT)))
    if not root.exists():
        raise FileNotFoundError(
            f"TranscriptMCP not found at {root}. Clone TranscriptMCP alongside SportSciMCP "
            "or set TRANSCRIPT_MCP_PATH."
        )
    path = str(root)
    if path not in sys.path:
        sys.path.insert(0, path)


def transcribe_youtube(url: str, language: str | None = None) -> dict[str, Any]:
    """Use TranscriptMCP functions (yt-dlp + Whisper) — same stack as transcript MCP."""
    _ensure_transcript_import()
    from transcript_mcp.server import (  # noqa: WPS433
        download_audio,
        get_video_info,
        transcribe_audio,
        TEMP_DIR,
    )

    info = get_video_info(url)
    if not info.get("success"):
        raise RuntimeError(info.get("error", "Failed to get video info"))

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir=TEMP_DIR) as tmp:
        audio_path = tmp.name + ".mp3"

    try:
        dl = download_audio(url, audio_path)
        if not dl.get("success"):
            raise RuntimeError(dl.get("error", "Download failed"))
        actual = dl["path"]
        tr = transcribe_audio(actual, language=language)
        if not tr.get("success"):
            raise RuntimeError(tr.get("error", "Transcription failed"))
        return {
            "url": url,
            "title": info.get("title", "YouTube video"),
            "channel": info.get("uploader", ""),
            "duration_sec": info.get("duration", 0),
            "transcript": tr.get("text", ""),
            "language": tr.get("language"),
        }
    finally:
        for p in (audio_path, audio_path.replace(".mp3", "")):
            try:
                if os.path.exists(p):
                    os.unlink(p)
            except OSError:
                pass


def ingest_youtube_research(
    url: str,
    notebook: str,
    *,
    title: str | None = None,
    language: str | None = None,
    wait: bool = False,
    save_brief_file: bool = False,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """
    Pipeline: YouTube → TranscriptMCP → NotebookLM (+ optional brief).
    """
    tx = transcribe_youtube(url, language=language)
    display_title = title or tx["title"]
    markdown = (
        f"# {display_title}\n\n"
        f"- **Source:** {url}\n"
        f"- **Channel:** {tx.get('channel', 'n/a')}\n"
        f"- **Duration (sec):** {tx.get('duration_sec', 'n/a')}\n\n"
        f"## Transcript\n\n{tx['transcript']}"
    )

    nlm_result = nlm.add_source(
        notebook,
        text=markdown,
        title=display_title,
        wait=wait,
    )

    result: dict[str, Any] = {
        "transcript_preview": (tx["transcript"] or "")[:500],
        "transcript_length": len(tx["transcript"] or ""),
        "notebooklm": nlm_result,
        "title": display_title,
    }

    if save_brief_file:
        rec = SearchRecord(
            source="youtube",
            id=url,
            type="webpage",
            title=display_title,
            url=url,
            abstract=(tx["transcript"] or "")[:2000],
            extra={"channel": tx.get("channel")},
        )
        result["brief"] = save_brief(rec, tags=tags or ["youtube"], notes=markdown[:8000])

    return result
