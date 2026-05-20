from __future__ import annotations

import httpx

from sportsci_mcp.adapters.base import LiteratureAdapter
from sportsci_mcp.config import openalex_email
from sportsci_mcp.models import SearchRecord

API = "https://api.openalex.org"


class OpenAlexAdapter(LiteratureAdapter):
    name = "openalex"

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=30.0,
            headers={"User-Agent": f"SportSciMCP ({openalex_email()})"},
        )

    def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> list[SearchRecord]:
        filters = []
        if year_from:
            filters.append(f"from_publication_date:{year_from}-01-01")
        if year_to:
            filters.append(f"to_publication_date:{year_to}-12-31")
        params: dict = {
            "search": query,
            "per_page": max_results,
            "mailto": openalex_email(),
        }
        if filters:
            params["filter"] = ",".join(filters)
        with self._client() as client:
            r = client.get(f"{API}/works", params=params)
            r.raise_for_status()
            results = r.json().get("results", [])
            return [self._work_to_record(w) for w in results]

    def get(self, record_id: str) -> SearchRecord:
        wid = record_id.replace("openalex:", "")
        if not wid.startswith("https://"):
            wid = f"https://openalex.org/{wid}"
        with self._client() as client:
            r = client.get(wid, params={"mailto": openalex_email()})
            r.raise_for_status()
            return self._work_to_record(r.json())

    def _work_to_record(self, work: dict) -> SearchRecord:
        oa_id = work.get("id", "").rsplit("/", 1)[-1]
        inv = work.get("authorships") or []
        authors = []
        for a in inv[:10]:
            name = (a.get("author") or {}).get("display_name")
            if name:
                authors.append(name)
        abstract = ""
        inv_abs = work.get("abstract_inverted_index")
        if inv_abs:
            abstract = self._reconstruct_abstract(inv_abs)
        doi = (work.get("doi") or "").replace("https://doi.org/", "")
        loc = work.get("primary_location") or {}
        source_name = (loc.get("source") or {}).get("display_name", "")
        return SearchRecord(
            source="openalex",
            id=oa_id,
            type="paper",
            title=work.get("display_name") or work.get("title") or "Untitled",
            url=work.get("id") or "",
            abstract=abstract,
            authors=authors,
            year=work.get("publication_year"),
            journal=source_name,
            doi=doi,
            extra={
                "cited_by_count": work.get("cited_by_count"),
                "is_open_access": (work.get("open_access") or {}).get("is_oa"),
                "oa_url": (work.get("open_access") or {}).get("oa_url"),
            },
        )

    @staticmethod
    def _reconstruct_abstract(inverted: dict) -> str:
        if not inverted:
            return ""
        max_pos = max(max(positions) for positions in inverted.values())
        words = [""] * (max_pos + 1)
        for word, positions in inverted.items():
            for p in positions:
                words[p] = word
        return " ".join(words).strip()
