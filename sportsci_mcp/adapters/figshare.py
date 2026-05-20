from __future__ import annotations

import httpx

from sportsci_mcp.adapters.base import DatasetAdapter
from sportsci_mcp.models import SearchRecord

API = "https://api.figshare.com/v2"


class FigshareAdapter(DatasetAdapter):
    name = "figshare"

    def search(
        self,
        query: str,
        *,
        max_results: int = 10,
    ) -> list[SearchRecord]:
        body = {
            "search_for": query,
            "page_size": max_results,
            "order": "published_date",
            "order_direction": "desc",
        }
        with httpx.Client(timeout=30.0) as client:
            r = client.post(f"{API}/articles/search", json=body)
            r.raise_for_status()
            items = r.json()
            if not isinstance(items, list):
                items = items.get("items", [])
            return [self._item_to_record(a) for a in items[:max_results]]

    def get(self, record_id: str) -> SearchRecord:
        aid = record_id.replace("figshare:", "")
        with httpx.Client(timeout=30.0) as client:
            r = client.get(f"{API}/articles/{aid}")
            r.raise_for_status()
            return self._item_to_record(r.json())

    def _item_to_record(self, item: dict) -> SearchRecord:
        aid = str(item.get("id", ""))
        title = item.get("title") or "Untitled"
        desc = item.get("description") or ""
        doi = item.get("doi") or ""
        url = item.get("url_public") or f"https://figshare.com/articles/{aid}"
        tags = item.get("tags") or item.get("defined_tags") or []
        return SearchRecord(
            source="figshare",
            id=aid,
            type="dataset",
            title=title,
            url=url,
            abstract=desc[:5000],
            doi=doi,
            tags=tags if isinstance(tags, list) else [],
            extra={
                "views": item.get("stats", {}).get("views") if isinstance(item.get("stats"), dict) else None,
                "downloads": item.get("stats", {}).get("downloads") if isinstance(item.get("stats"), dict) else None,
            },
        )
