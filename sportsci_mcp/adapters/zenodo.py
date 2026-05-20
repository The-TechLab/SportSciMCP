from __future__ import annotations

import httpx

from sportsci_mcp.adapters.base import DatasetAdapter
from sportsci_mcp.models import SearchRecord

API = "https://zenodo.org/api"


class ZenodoAdapter(DatasetAdapter):
    name = "zenodo"

    def search(
        self,
        query: str,
        *,
        max_results: int = 10,
    ) -> list[SearchRecord]:
        params = {
            "q": query,
            "size": max_results,
            "type": "dataset",
            "sort": "bestmatch",
        }
        with httpx.Client(timeout=30.0) as client:
            r = client.get(f"{API}/records", params=params)
            r.raise_for_status()
            hits = r.json().get("hits", {}).get("hits", [])
            return [self._hit_to_record(h) for h in hits]

    def get(self, record_id: str) -> SearchRecord:
        rid = record_id.replace("zenodo:", "")
        with httpx.Client(timeout=30.0) as client:
            r = client.get(f"{API}/records/{rid}")
            r.raise_for_status()
            return self._hit_to_record(r.json())

    def _hit_to_record(self, hit: dict) -> SearchRecord:
        meta = hit.get("metadata") or hit
        rid = str(hit.get("id") or meta.get("id", ""))
        title = meta.get("title") or "Untitled"
        desc = meta.get("description") or ""
        creators = [c.get("name", "") for c in meta.get("creators", []) if c.get("name")]
        license_id = (meta.get("license") or {}).get("id", "") if isinstance(meta.get("license"), dict) else str(meta.get("license") or "")
        files = hit.get("files") or []
        size_mb = sum((f.get("size") or 0) for f in files) / (1024 * 1024) if files else None
        year_raw = (meta.get("publication_date") or "")[:4]
        year = int(year_raw) if year_raw.isdigit() else None
        return SearchRecord(
            source="zenodo",
            id=rid,
            type="dataset",
            title=title,
            url=hit.get("links", {}).get("html") or f"https://zenodo.org/record/{rid}",
            abstract=desc[:3000],
            authors=creators,
            year=year,
            license=license_id,
            tags=[k.get("term", "") for k in (meta.get("keywords") or []) if isinstance(k, dict)] or list(meta.get("keywords") or []),
            extra={
                "doi": meta.get("doi"),
                "file_count": len(files),
                "size_mb": round(size_mb, 2) if size_mb else None,
            },
        )
