from __future__ import annotations

import os

import httpx

from sportsci_mcp.adapters.base import LiteratureAdapter
from sportsci_mcp.models import SearchRecord

API = "https://api.semanticscholar.org/graph/v1"
FIELDS = "paperId,title,abstract,year,authors,externalIds,url,citationCount,journal"


class SemanticScholarAdapter(LiteratureAdapter):
    name = "semantic_scholar"

    def _headers(self) -> dict:
        key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
        return {"x-api-key": key} if key else {}

    def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> list[SearchRecord]:
        params: dict = {"query": query, "limit": max_results, "fields": FIELDS}
        if year_from:
            params["year"] = f"{year_from}-{year_to or 2099}"
        with httpx.Client(timeout=30.0, headers=self._headers()) as client:
            r = client.get(f"{API}/paper/search", params=params)
            if r.status_code == 429:
                raise RuntimeError(
                    "Semantic Scholar rate limit (429). Retry later or set SEMANTIC_SCHOLAR_API_KEY."
                )
            r.raise_for_status()
            data = r.json().get("data") or []
            return [self._paper_to_record(p) for p in data]

    def get(self, record_id: str) -> SearchRecord:
        pid = record_id.replace("semantic_scholar:", "").replace("s2:", "")
        with httpx.Client(timeout=30.0, headers=self._headers()) as client:
            r = client.get(f"{API}/paper/{pid}", params={"fields": FIELDS})
            r.raise_for_status()
            return self._paper_to_record(r.json())

    def _paper_to_record(self, paper: dict) -> SearchRecord:
        authors = [(a.get("name") or "") for a in (paper.get("authors") or [])]
        ext = paper.get("externalIds") or {}
        doi = ext.get("DOI", "")
        journal = (paper.get("journal") or {}).get("name", "")
        return SearchRecord(
            source="semantic_scholar",
            id=paper.get("paperId", ""),
            type="paper",
            title=paper.get("title") or "Untitled",
            url=paper.get("url") or f"https://www.semanticscholar.org/paper/{paper.get('paperId')}",
            abstract=paper.get("abstract") or "",
            authors=authors,
            year=paper.get("year"),
            journal=journal,
            doi=doi,
            extra={
                "citation_count": paper.get("citationCount"),
                "pmid": ext.get("PubMed"),
            },
        )
