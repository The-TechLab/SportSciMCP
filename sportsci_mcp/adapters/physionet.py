from __future__ import annotations

import re
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

from sportsci_mcp.adapters.base import DatasetAdapter
from sportsci_mcp.adapters.scrape import fetch_page
from sportsci_mcp.models import SearchRecord


class PhysioNetAdapter(DatasetAdapter):
    """PhysioNet project discovery via public index pages (no API key)."""

    name = "physionet"
    INDEX_URL = "https://physionet.org/about/database/"

    def search(
        self,
        query: str,
        *,
        max_results: int = 10,
    ) -> list[SearchRecord]:
        q = query.lower()
        html, _ = fetch_page(self.INDEX_URL)
        soup = BeautifulSoup(html, "html.parser")
        records: list[SearchRecord] = []
        for a in soup.select('a[href*="/content/"]'):
            href = a.get("href", "")
            m = re.search(r"/content/([^/?#]+)/?", href)
            if not m:
                continue
            slug = m.group(1)
            if slug in {"types"} or slug in {r.id for r in records}:
                continue
            title = a.get_text(strip=True)
            if len(title) < 3:
                title = slug.replace("-", " ").title()
            haystack = f"{slug} {title}".lower()
            if q not in haystack and not all(w in haystack for w in q.split() if len(w) > 2):
                continue
            full = href if href.startswith("http") else urljoin("https://physionet.org", href)
            records.append(
                SearchRecord(
                    source="physionet",
                    id=slug,
                    type="dataset",
                    title=title,
                    url=full,
                    extra={"access": "see project page; some require credentialed login"},
                )
            )
            if len(records) >= max_results:
                break
        return records

    def get(self, record_id: str) -> SearchRecord:
        slug = record_id.replace("physionet:", "")
        url = f"https://physionet.org/content/{slug}/"
        html, final = fetch_page(url)
        soup = BeautifulSoup(html, "html.parser")
        title = soup.find("h1")
        title_text = title.get_text(strip=True) if title else slug
        desc = ""
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            desc = meta["content"]
        else:
            p = soup.find("p")
            desc = p.get_text(strip=True) if p else ""
        return SearchRecord(
            source="physionet",
            id=slug,
            type="dataset",
            title=title_text,
            url=final,
            abstract=desc[:3000],
            extra={
                "download_note": "Use PhysioNet website or wget; credentialed access may apply",
            },
        )
