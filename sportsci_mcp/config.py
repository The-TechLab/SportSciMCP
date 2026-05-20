from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_PKG_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _PKG_ROOT.parent
_CONFIG_DIR = _REPO_ROOT / "config"
_DATA_DIR = _PKG_ROOT / "data"


def _load_yaml(name: str) -> dict[str, Any]:
    path = _CONFIG_DIR / name
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def sources_config() -> dict[str, Any]:
    return _load_yaml("sources.yaml")


def notebooks_config() -> dict[str, Any]:
    return _load_yaml("notebooks.yaml")


def data_dir() -> Path:
    return _DATA_DIR


def briefs_dir() -> Path:
    env = os.environ.get("SPORTSCI_BRIEFS_DIR")
    if env:
        return Path(env)
    cfg = notebooks_config()
    if cfg.get("briefs_dir"):
        return Path(cfg["briefs_dir"])
    return Path.home() / "QAI-Lab-Drive" / "research-briefs"


def resolve_notebook_id(alias_or_id: str) -> tuple[str, str]:
    """Return (uuid, display_title). Accepts alias or raw UUID."""
    cfg = notebooks_config()
    notebooks = cfg.get("notebooks") or {}
    key = alias_or_id.strip().lower().replace(" ", "_").replace("-", "_")
    if key in notebooks:
        entry = notebooks[key]
        return entry["id"], entry.get("title", key)
    if len(alias_or_id) >= 32 and "-" in alias_or_id:
        return alias_or_id, alias_or_id
    default = cfg.get("default")
    if default and default in notebooks:
        entry = notebooks[default]
        return entry["id"], entry.get("title", default)
    raise ValueError(
        f"Unknown notebook alias '{alias_or_id}'. "
        f"Use notebooklm_list_notebooks for aliases."
    )


def openalex_email() -> str:
    return os.environ.get("OPENALEX_EMAIL", "will@thetechlab.info")


def pubmed_email() -> str:
    return os.environ.get("PUBMED_EMAIL", "will@thetechlab.info")


def has_env_credentials(env_vars: list[str]) -> bool:
    return all(os.environ.get(k, "").strip() for k in env_vars)


def env_var(name: str) -> str:
    return os.environ.get(name, "").strip()


def credentials_status(entry: dict[str, Any]) -> str:
    """Return none | optional | configured | missing."""
    api = entry.get("api_key_env")
    creds = entry.get("credentials_env") or []
    if isinstance(api, str):
        api_list = [api]
    else:
        api_list = list(api or [])
    env_list = api_list + list(creds)
    if not env_list:
        return "none"
    if not entry.get("requires_auth"):
        if any(env_var(k) for k in env_list):
            return "configured"
        return "optional"
    if has_env_credentials(env_list) if creds else any(env_var(k) for k in api_list):
        return "configured"
    return "missing"


def entry_is_active(entry: dict[str, Any]) -> bool:
    """Source is enabled in yaml and auth requirements are satisfied."""
    if not entry.get("enabled", False):
        return False
    if not entry.get("requires_auth"):
        return True
    api = entry.get("api_key_env")
    if isinstance(api, str) and not env_var(api):
        return False
    creds = entry.get("credentials_env") or []
    if creds and not has_env_credentials(creds):
        return False
    return True


def skip_reason(entry: dict[str, Any], name: str) -> str:
    if not entry.get("enabled"):
        return "disabled in config/sources.yaml (set enabled: true)"
    if entry.get("requires_auth"):
        api = entry.get("api_key_env")
        creds = entry.get("credentials_env") or []
        if api and not env_var(api):
            return f"set {api} in ~/.cursor/mcp-secrets.env"
        if creds and not has_env_credentials(creds):
            return f"set {' and '.join(creds)} in ~/.cursor/mcp-secrets.env"
    return "unknown or unavailable"
