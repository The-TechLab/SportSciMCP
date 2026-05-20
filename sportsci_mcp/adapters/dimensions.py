from __future__ import annotations

import httpx

from sportsci_mcp.adapters.base import LiteratureAdapter
from sportsci_mcp.config import env_var
from sportsci_mcp.models import SearchRecord

API = "https://app.dimensions.ai/api/dsl/v2"


class DimensionsAdapter(LiteratureAdapter):
    name = "dimensions"

    def _require_key(self) -> str:
        key = env_var("DIMENSIONS_API_KEY")
        if not key:
            raise RuntimeError(
                "DIMENSIONS_API_KEY not set. Get a key from https://app.dimensions.ai "
                "and add to ~/.cursor/mcp-secrets.env"
            )
        return key

    def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> list[SearchRecord]:
        key = self._require_key()
        year_clause = ""
        if year_from or year_to:
            yf = year_from or 1900
            yt = year_to or 2099
            year_clause = f" and year in [{yf}:{yt}]"
        dsl = f'search publications in full_data for "{query}"{year_clause} return publications[basics+abstract] limit {max_results}'
        with httpx.Client(timeout=60.0) as client:
            r = client.post(
                API,
                json={"query": dsl, "limit": max_results},
                headers={"Authorization": f"Key {key}", "Content-Type": "application/json"},
            )
            r.raise_for_status()
            pubs = r.json().get("publications") or []
            return [self._pub_to_record(p) for p in pubs]

    def get(self, record_id: str) -> SearchRecord:
        key = self._require_key()
        pid = record_id.replace("dimensions:", "")
        dsl = f'fetch publications where id = "{pid}" return publications[basics+abstract]'
        with httpx.Client(timeout=60.0) as client:
            r = client.post(
                API,
                json={"query": dsl},
                headers={"Authorization": f"Key {key}", "Content-Type": "application/json"},
            )
            r.raise_for_status()
            pubs = r.json().get("publications") or []
            if not pubs:
                raise ValueError(f"Dimensions publication not found: {pid}")
            return self._pub_to_record(pubs[0])

    def _pub_to_record(self, pub: dict) -> SearchRecord:
        authors = [a.get("full_name", a.get("name", "")) for a in (pub.get("authors") or [])]
        return SearchRecord(
            source="dimensions",
            id=pub.get("id", ""),
            type="paper",
            title=pub.get("title") or "Untitled",
            url=f"https://app.dimensions.ai/details/publication/{pub.get('id')}",
            abstract=(pub.get("abstract") or "")[:5000],
            authors=authors,
            year=pub.get("year"),
            journal=(pub.get("journal") or {}).get("title", ""),
            doi=(pub.get("doi") or ""),
            extra={"times_cited": pub.get("times_cited")},
        )
