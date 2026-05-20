from __future__ import annotations

import os

import httpx

from sportsci_mcp.adapters.base import LiteratureAdapter
from sportsci_mcp.config import env_var
from sportsci_mcp.models import SearchRecord

API = "https://api.core.ac.uk/v3"


class CoreAdapter(LiteratureAdapter):
    name = "core"

    def _headers(self) -> dict:
        key = env_var("CORE_API_KEY")
        return {"Authorization": f"Bearer {key}"} if key else {}

    def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> list[SearchRecord]:
        q = query
        if year_from:
            q += f" AND yearPublished>={year_from}"
        if year_to:
            q += f" AND yearPublished<={year_to}"
        params = {"q": q, "limit": max_results, "offset": 0}
        with httpx.Client(timeout=30.0, headers=self._headers(), follow_redirects=True) as client:
            r = client.get(f"{API}/search/works/", params=params)
            r.raise_for_status()
            results = r.json().get("results") or []
            return [self._work_to_record(w) for w in results]

    def get(self, record_id: str) -> SearchRecord:
        wid = record_id.replace("core:", "")
        with httpx.Client(timeout=30.0, headers=self._headers(), follow_redirects=True) as client:
            r = client.get(f"{API}/outputs/{wid}/works" if not wid.isdigit() else f"{API}/works/{wid}")
            if r.status_code == 404:
                r = client.get(f"{API}/outputs/{wid}")
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list) and data:
                return self._work_to_record(data[0])
            if isinstance(data, dict) and "results" in data:
                hits = data["results"]
                if hits:
                    return self._work_to_record(hits[0])
            return self._work_to_record(data)

    @staticmethod
    def _journal_name(work: dict) -> str:
        journals = work.get("journals")
        if isinstance(journals, list) and journals:
            return str(journals[0])
        return str(work.get("publisher") or "")

    def _work_to_record(self, work: dict) -> SearchRecord:
        authors = [a.get("name", "") for a in (work.get("authors") or []) if a.get("name")]
        oa_id = str(work.get("id") or work.get("coreId") or "")
        doi = work.get("doi") or ""
        year_raw = work.get("yearPublished") or work.get("publishedDate", "")[:4]
        year = int(year_raw) if str(year_raw).isdigit() else None
        return SearchRecord(
            source="core",
            id=oa_id,
            type="paper",
            title=work.get("title") or "Untitled",
            url=doi and f"https://doi.org/{doi}" or f"https://core.ac.uk/works/{oa_id}",
            abstract=(work.get("abstract") or "")[:5000],
            authors=authors,
            year=year,
            journal=self._journal_name(work),
            doi=doi,
            extra={
                "citation_count": work.get("citationCount"),
                "download_url": (work.get("downloadUrl") or work.get("fullTextLink")),
                "api_key_used": bool(os.environ.get("CORE_API_KEY")),
            },
        )
