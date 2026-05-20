from __future__ import annotations

import os

import httpx

from sportsci_mcp.adapters.base import DatasetAdapter
from sportsci_mcp.config import has_env_credentials
from sportsci_mcp.models import SearchRecord

API = "https://www.kaggle.com/api/v1"


class KaggleAdapter(DatasetAdapter):
    name = "kaggle"
    requires_auth = True

    def _auth(self) -> tuple[str, str] | None:
        user = os.environ.get("KAGGLE_USERNAME", "")
        key = os.environ.get("KAGGLE_KEY", "")
        if user and key:
            return user, key
        return None

    def available(self) -> bool:
        return has_env_credentials(["KAGGLE_USERNAME", "KAGGLE_KEY"])

    def search(
        self,
        query: str,
        *,
        max_results: int = 10,
    ) -> list[SearchRecord]:
        auth = self._auth()
        if not auth:
            raise RuntimeError(
                "Kaggle credentials missing. Set KAGGLE_USERNAME and KAGGLE_KEY in ~/.cursor/mcp-secrets.env"
            )
        params = {"search": query, "page": 1, "pageSize": max_results}
        with httpx.Client(timeout=30.0, auth=auth) as client:
            r = client.get(f"{API}/datasets/list", params=params)
            r.raise_for_status()
            items = r.json()
            if not isinstance(items, list):
                items = items.get("datasets", items) if isinstance(items, dict) else []
            return [self._item_to_record(d) for d in items[:max_results]]

    def get(self, record_id: str) -> SearchRecord:
        auth = self._auth()
        if not auth:
            raise RuntimeError("Kaggle credentials missing")
        rid = record_id.replace("kaggle:", "")
        if "/" not in rid:
            raise ValueError("Kaggle id must be owner/slug")
        owner, slug = rid.split("/", 1)
        with httpx.Client(timeout=30.0, auth=auth) as client:
            r = client.get(f"{API}/datasets/view/{owner}/{slug}")
            r.raise_for_status()
            return self._item_to_record(r.json())

    def _item_to_record(self, item: dict) -> SearchRecord:
        owner = item.get("ownerRef") or item.get("creatorName") or item.get("ownerSlug", "")
        if isinstance(owner, dict):
            owner = owner.get("userName", owner.get("name", ""))
        slug = item.get("datasetSlug") or item.get("ref", "")
        ref = f"{owner}/{slug}".strip("/")
        title = item.get("title") or item.get("name") or slug
        subtitle = item.get("subtitle") or item.get("description") or ""
        size = item.get("totalBytes") or item.get("size")
        return SearchRecord(
            source="kaggle",
            id=ref,
            type="dataset",
            title=title,
            url=f"https://www.kaggle.com/datasets/{ref}",
            abstract=subtitle[:3000],
            authors=[str(owner)] if owner else [],
            license=item.get("licenseName") or item.get("license", ""),
            tags=item.get("tags") or item.get("topics") or [],
            extra={
                "downloads": item.get("downloadCount") or item.get("totalDownloads"),
                "votes": item.get("voteCount"),
                "size_bytes": size,
                "last_updated": item.get("lastUpdated") or item.get("updateDate"),
            },
        )
