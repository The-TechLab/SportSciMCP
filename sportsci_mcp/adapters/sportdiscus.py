from __future__ import annotations

import httpx

from sportsci_mcp.adapters.base import LiteratureAdapter
from sportsci_mcp.config import env_var, has_env_credentials
from sportsci_mcp.models import SearchRecord

# EBSCO EDS API — institutional SPORTDiscus access via your library credentials.
EDS = "https://eadsapi.ebscohost.com/edsapi/rest"


class SportDiscusAdapter(LiteratureAdapter):
    name = "sportdiscus"

    def available(self) -> bool:
        return has_env_credentials(["EBSCO_USER_ID", "EBSCO_PASSWORD"])

    def _session_token(self, client: httpx.Client) -> str:
        profile = env_var("EBSCO_PROFILE") or "eds"
        r = client.post(
            f"{EDS}/CreateSession",
            json={
                "UserId": env_var("EBSCO_USER_ID"),
                "Password": env_var("EBSCO_PASSWORD"),
                "Profile": profile,
                "Guest": "n",
            },
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        data = r.json()
        token = (
            data.get("SessionToken")
            or (data.get("CreateSessionResponse") or {}).get("SessionToken")
            or ""
        )
        if not token:
            raise RuntimeError(f"EBSCO session failed: {data}")
        return token

    def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> list[SearchRecord]:
        if not self.available():
            raise RuntimeError(
                "SPORTDiscus uses EBSCO EDS. Set EBSCO_USER_ID and EBSCO_PASSWORD "
                "(from your institution) in ~/.cursor/mcp-secrets.env"
            )
        with httpx.Client(timeout=45.0) as client:
            token = self._session_token(client)
            params: dict = {
                "query": query,
                "searchmode": "smart",
                "resultsperpage": max_results,
                "pagenumber": 1,
                "highlight": "n",
                "includefacets": "n",
                "view": "brief",
                "routing": "eds",
                "sessiontoken": token,
            }
            if year_from:
                params["limiter"] = f"DT {year_from}-{year_to or 2099}"
            r = client.get(f"{EDS}/Search", params=params)
            r.raise_for_status()
            data = r.json()
            records_block = (
                data.get("SearchResult", {})
                .get("Data", {})
                .get("Records", [])
            )
            if not records_block:
                records_block = data.get("Records") or []
            out: list[SearchRecord] = []
            for rec in records_block[:max_results]:
                out.append(self._record_to_search(rec))
            return out

    def get(self, record_id: str) -> SearchRecord:
        rid = record_id.replace("sportdiscus:", "")
        return self.search(rid, max_results=1)[0]

    def _record_to_search(self, rec: dict) -> SearchRecord:
        header = rec.get("Header") or {}
        title = header.get("Title") or rec.get("Title") or "Untitled"
        db_label = header.get("DbLabel") or header.get("DbId") or "SPORTDiscus"
        an = header.get("An") or rec.get("An") or rec.get("ResultId") or title[:20]
        url = header.get("PLink") or header.get("Link") or ""
        abstract = ""
        for item in rec.get("Items") or []:
            if item.get("Name") in ("Abstract", "AB"):
                abstract = item.get("Data") or ""
                break
        return SearchRecord(
            source="sportdiscus",
            id=str(an),
            type="paper",
            title=title,
            url=url or f"https://research.ebsco.com/c/{an}",
            abstract=abstract[:5000],
            journal=db_label,
            extra={"ebsco_an": an},
        )
