from __future__ import annotations

from sportsci_mcp.adapters.arxiv import ArxivAdapter
from sportsci_mcp.adapters.base import DatasetAdapter, LiteratureAdapter
from sportsci_mcp.adapters.core import CoreAdapter
from sportsci_mcp.adapters.dimensions import DimensionsAdapter
from sportsci_mcp.adapters.html_search import (
    MendeleyDataAdapter,
    MotrpacAdapter,
    ScoreNetworkAdapter,
    SimtkAdapter,
)
from sportsci_mcp.adapters.kaggle import KaggleAdapter
from sportsci_mcp.adapters.openalex import OpenAlexAdapter
from sportsci_mcp.adapters.physionet import PhysioNetAdapter
from sportsci_mcp.adapters.pubmed import PubMedAdapter
from sportsci_mcp.adapters.scrape import ScrapeAdapter, SsrnAdapter
from sportsci_mcp.adapters.osf import OsfAdapter
from sportsci_mcp.adapters.figshare import FigshareAdapter
from sportsci_mcp.adapters.semantic_scholar import SemanticScholarAdapter
from sportsci_mcp.adapters.sportdiscus import SportDiscusAdapter
from sportsci_mcp.adapters.zenodo import ZenodoAdapter
from sportsci_mcp.config import credentials_status, entry_is_active, skip_reason, sources_config
from sportsci_mcp.models import SearchRecord

LITERATURE_REGISTRY: dict[str, type[LiteratureAdapter]] = {
    "pubmed": PubMedAdapter,
    "openalex": OpenAlexAdapter,
    "ssrn": SsrnAdapter,
    "arxiv": ArxivAdapter,
    "semantic_scholar": SemanticScholarAdapter,
    "core": CoreAdapter,
    "dimensions": DimensionsAdapter,
    "scorenetwork": ScoreNetworkAdapter,
    "osf": OsfAdapter,
    "sportdiscus": SportDiscusAdapter,
}

DATASET_REGISTRY: dict[str, type[DatasetAdapter]] = {
    "kaggle": KaggleAdapter,
    "physionet": PhysioNetAdapter,
    "zenodo": ZenodoAdapter,
    "simtk": SimtkAdapter,
    "motrpac": MotrpacAdapter,
    "mendeley_data": MendeleyDataAdapter,
    "figshare": FigshareAdapter,
}


def _lit_cfg() -> dict:
    return sources_config().get("literature") or {}


def _ds_cfg() -> dict:
    return sources_config().get("datasets") or {}


def literature_adapters(names: list[str] | None = None) -> list[LiteratureAdapter]:
    cfg = _lit_cfg()
    out: list[LiteratureAdapter] = []
    for name, cls in LITERATURE_REGISTRY.items():
        if names and name not in names:
            continue
        entry = cfg.get(name) or {}
        if not entry_is_active(entry):
            continue
        adapter = cls()
        if name == "sportdiscus" and hasattr(adapter, "available") and not adapter.available():
            continue
        out.append(adapter)
    return out


def dataset_adapters(names: list[str] | None = None) -> list[DatasetAdapter]:
    cfg = _ds_cfg()
    out: list[DatasetAdapter] = []
    for name, cls in DATASET_REGISTRY.items():
        if names and name not in names:
            continue
        entry = cfg.get(name) or {}
        if not entry_is_active(entry):
            continue
        adapter = cls()
        if name == "kaggle" and hasattr(adapter, "available") and not adapter.available():
            continue
        out.append(adapter)
    return out


def _skipped_sources(
    requested: list[str] | None,
    active: set[str],
    cfg: dict,
) -> list[dict]:
    skipped: list[dict] = []
    if not requested:
        return skipped
    for s in requested:
        if s in active:
            continue
        entry = cfg.get(s) or {}
        skipped.append({"source": s, "reason": skip_reason(entry, s)})
    return skipped


def search_literature(
    query: str,
    *,
    sources: list[str] | None = None,
    max_results_per_source: int = 10,
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict:
    adapters = literature_adapters(sources)
    cfg = _lit_cfg()
    skipped = _skipped_sources(sources, {a.name for a in adapters}, cfg)
    merged: list[SearchRecord] = []
    by_source: dict[str, int] = {}
    errors: list[dict] = []

    for adapter in adapters:
        try:
            hits = adapter.search(
                query,
                max_results=max_results_per_source,
                year_from=year_from,
                year_to=year_to,
            )
            merged.extend(hits)
            by_source[adapter.name] = len(hits)
        except Exception as e:
            errors.append({"source": adapter.name, "error": str(e)})

    return {
        "query": query,
        "total": len(merged),
        "by_source": by_source,
        "skipped": skipped,
        "errors": errors,
        "results": [r.to_dict() for r in merged],
    }


def search_datasets(
    query: str,
    *,
    sources: list[str] | None = None,
    max_results_per_source: int = 10,
) -> dict:
    adapters = dataset_adapters(sources)
    cfg = _ds_cfg()
    skipped = _skipped_sources(sources, {a.name for a in adapters}, cfg)
    merged: list[SearchRecord] = []
    by_source: dict[str, int] = {}
    errors: list[dict] = []

    for adapter in adapters:
        try:
            hits = adapter.search(query, max_results=max_results_per_source)
            merged.extend(hits)
            by_source[adapter.name] = len(hits)
        except Exception as e:
            errors.append({"source": adapter.name, "error": str(e)})

    return {
        "query": query,
        "total": len(merged),
        "by_source": by_source,
        "skipped": skipped,
        "errors": errors,
        "results": [r.to_dict() for r in merged],
    }


def search_all(
    query: str,
    *,
    literature_sources: list[str] | None = None,
    dataset_sources: list[str] | None = None,
    max_results_per_source: int = 10,
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict:
    """Search literature and datasets in one call."""
    lit = search_literature(
        query,
        sources=literature_sources,
        max_results_per_source=max_results_per_source,
        year_from=year_from,
        year_to=year_to,
    )
    ds = search_datasets(
        query,
        sources=dataset_sources,
        max_results_per_source=max_results_per_source,
    )
    return {
        "query": query,
        "literature": lit,
        "datasets": ds,
        "total": lit["total"] + ds["total"],
    }


def scrape_adapter() -> ScrapeAdapter:
    return ScrapeAdapter()


def _adapter_map() -> dict[str, LiteratureAdapter | DatasetAdapter]:
    mapping: dict[str, LiteratureAdapter | DatasetAdapter] = {}
    for a in literature_adapters(None):
        mapping[a.name] = a
    for a in dataset_adapters(None):
        mapping[a.name] = a
    return mapping


def get_record(ref: str) -> SearchRecord:
    if ":" not in ref:
        raise ValueError(
            "Use format source:id (e.g. pubmed:123, kaggle:owner/slug, core:456, simtk:proj)"
        )
    source, rid = ref.split(":", 1)
    source = source.lower()
    if source == "url":
        return scrape_adapter().fetch(rid)
    if source == "s2":
        source = "semantic_scholar"
    adapters = _adapter_map()
    if source not in adapters:
        raise ValueError(
            f"Unknown source '{source}'. Use list_sources. "
            f"Known: {', '.join(sorted(adapters))}, url"
        )
    return adapters[source].get(rid)


def list_sources_status() -> dict:
    cfg = sources_config()
    lit = cfg.get("literature") or {}
    ds = cfg.get("datasets") or {}
    scrape = cfg.get("scrape") or {}
    items = []

    for name, entry in lit.items():
        items.append(
            {
                "name": name,
                "category": "literature",
                "enabled": bool(entry.get("enabled")),
                "active": entry_is_active(entry),
                "phase": entry.get("phase", "?"),
                "auth": entry.get("api_key_env") or entry.get("credentials_env") or "none",
                "credentials": credentials_status(entry),
                "notes": entry.get("notes") or entry.get("mode", ""),
            }
        )

    for name, entry in ds.items():
        items.append(
            {
                "name": name,
                "category": "datasets",
                "enabled": bool(entry.get("enabled")),
                "active": entry_is_active(entry),
                "phase": entry.get("phase", 2),
                "auth": entry.get("api_key_env") or entry.get("credentials_env") or "none",
                "credentials": credentials_status(entry),
                "notes": entry.get("notes") or entry.get("mode", ""),
            }
        )

    items.append(
        {
            "name": "scrape_url",
            "category": "scrape",
            "enabled": bool((scrape.get("generic") or {}).get("enabled", True)),
            "active": True,
            "phase": 1,
            "auth": "none",
            "credentials": "none",
            "notes": "generic HTML; no API key",
        }
    )
    return {
        "sources": items,
        "version": "0.4.0",
        "phase3_tools": _phase3_tools_status(),
        "phase4_tools": _phase4_tools_status(),
    }


def _phase3_tools_status() -> list[str]:
    return [
        "parse_session_csv",
        "calc_training_load",
        "lookup_norms",
        "rtp_checklist",
        "compare_papers",
        "build_literature_review_outline",
    ]


def _phase4_tools_status() -> list[str]:
    return ["search_all", "ingest_youtube_research"]
