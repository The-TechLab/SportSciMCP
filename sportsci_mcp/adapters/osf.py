from __future__ import annotations

import httpx

from sportsci_mcp.adapters.base import LiteratureAdapter
from sportsci_mcp.models import SearchRecord

API = "https://api.osf.io/v2"


class OsfAdapter(LiteratureAdapter):
    name = "osf"

    def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> list[SearchRecord]:
        params = {"q": query, "page[size]": min(max_results * 3, 50)}
        with httpx.Client(timeout=30.0) as client:
            r = client.get(f"{API}/search/", params=params)
            r.raise_for_status()
            data = r.json().get("data") or []
            records: list[SearchRecord] = []
            for item in data:
                if not item or item.get("type") != "preprints":
                    continue
                rec = self._item_to_record(item)
                if year_from and rec.year and rec.year < year_from:
                    continue
                if year_to and rec.year and rec.year > year_to:
                    continue
                records.append(rec)
                if len(records) >= max_results:
                    break
            if records:
                return records
            # Fallback: recent preprints filtered by title/description
            r2 = client.get(
                f"{API}/preprints/",
                params={"page[size]": min(max_results * 5, 50)},
            )
            r2.raise_for_status()
            q = query.lower()
            for item in r2.json().get("data") or []:
                if not item:
                    continue
                rec = self._item_to_record(item)
                hay = f"{rec.title} {rec.abstract}".lower()
                if q not in hay and not all(w in hay for w in q.split() if len(w) > 2):
                    continue
                records.append(rec)
                if len(records) >= max_results:
                    break
            return records

    def get(self, record_id: str) -> SearchRecord:
        pid = record_id.replace("osf:", "")
        with httpx.Client(timeout=30.0) as client:
            r = client.get(f"{API}/preprints/{pid}/")
            r.raise_for_status()
            return self._item_to_record(r.json().get("data") or r.json())

    def _item_to_record(self, item: dict) -> SearchRecord:
        attrs = item.get("attributes") or item
        pid = item.get("id") or attrs.get("guid", "")
        title = attrs.get("title") or "Untitled"
        desc = attrs.get("description") or ""
        tags = attrs.get("tags") or []
        doi = attrs.get("doi") or ""
        date = (attrs.get("date_published") or attrs.get("original_publication_date") or "")[:4]
        year = int(date) if date.isdigit() else None
        links = item.get("links") or {}
        html = links.get("html") or f"https://osf.io/preprints/{pid}"
        return SearchRecord(
            source="osf",
            id=pid,
            type="paper",
            title=title,
            url=html,
            abstract=desc[:5000],
            year=year,
            doi=doi.replace("https://doi.org/", "") if doi else "",
            tags=tags if isinstance(tags, list) else [],
            extra={"node": "preprint"},
        )
