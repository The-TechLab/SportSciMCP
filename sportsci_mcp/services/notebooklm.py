from __future__ import annotations

import json
import subprocess
from typing import Any

from sportsci_mcp.config import notebooks_config, resolve_notebook_id


def list_notebooks() -> dict[str, Any]:
    cfg = notebooks_config()
    aliases = {
        alias: {"id": entry["id"], "title": entry.get("title", alias)}
        for alias, entry in (cfg.get("notebooks") or {}).items()
    }
    nlm_list: list = []
    try:
        proc = subprocess.run(
            ["nlm", "notebook", "list"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            nlm_list = json.loads(proc.stdout)
    except (json.JSONDecodeError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return {
        "default_alias": cfg.get("default"),
        "aliases": aliases,
        "remote_notebooks": nlm_list,
    }


def add_source(
    notebook: str,
    *,
    url: str | None = None,
    text: str | None = None,
    title: str | None = None,
    wait: bool = False,
) -> dict[str, Any]:
    nb_id, nb_title = resolve_notebook_id(notebook)
    cmd = ["nlm", "source", "add", nb_id]
    if url:
        cmd.extend(["--url", url])
    elif text:
        cmd.extend(["--text", text])
    else:
        raise ValueError("Provide url or text")
    if title:
        cmd.extend(["--title", title])
    if wait:
        cmd.append("--wait")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300 if wait else 120)
    return {
        "ok": proc.returncode == 0,
        "notebook_id": nb_id,
        "notebook_title": nb_title,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "command": " ".join(cmd[:4]) + " ...",
    }
