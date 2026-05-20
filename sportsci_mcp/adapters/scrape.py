from __future__ import annotations

import re
import time
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

from sportsci_mcp.adapters.base import LiteratureAdapter
from sportsci_mcp.config import sources_config
from sportsci_mcp.models import SearchRecord

_last_request = 0.0
_MIN_INTERVAL = 1.0


def _rate_limit() -> None:
    global _last_request
    now = time.time()
    wait = _MIN_INTERVAL - (now - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.time()


def _user_agent() -> str:
    cfg = sources_config()
    return (cfg.get("scrape") or {}).get("generic", {}).get(
        "user_agent",
        "SportSciMCP/0.1 (research)",
    )


def fetch_page(url: str) -> tuple[str, str]:
    """Return (html, final_url)."""
    _rate_limit()
    with httpx.Client(
        timeout=30.0,
        follow_redirects=True,
        headers={"User-Agent": _user_agent()},
    ) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.text, str(r.url)


def extract_readable_text(html: str, url: str) -> SearchRecord:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    title = soup.title.get_text(strip=True) if soup.title else url
    main = (
        soup.find("article")
        or soup.find("main")
        or soup.find(class_=re.compile(r"content|article|abstract", re.I))
        or soup.body
    )
    text = main.get_text(separator="\n", strip=True) if main else soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)[:50000]
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower())[:80].strip("-") or "page"
    return SearchRecord(
        source="scrape",
        id=slug,
        type="webpage",
        title=title,
        url=url,
        abstract=text[:2000],
        extra={"full_text_length": len(text), "full_text": text},
    )


class ScrapeAdapter:
    """Generic URL scrape — not a LiteratureAdapter search."""

    name = "scrape"

    def fetch(self, url: str) -> SearchRecord:
        html, final_url = fetch_page(url)
        return extract_readable_text(html, final_url)


class SsrnAdapter(LiteratureAdapter):
    """SSRN search via public HTML (no API key). Best-effort."""

    name = "ssrn"

    def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> list[SearchRecord]:
        url = f"https://papers.ssrn.com/sol3/results.cfm?RequestTimeout=50000000&npage=1&txtKey1={quote_plus(query)}"
        html, _ = fetch_page(url)
        soup = BeautifulSoup(html, "html.parser")
        records: list[SearchRecord] = []
        for link in soup.select("a[href*='abstract_id='], a[href*='papers.cfm?abstract_id=']"):
            href = link.get("href", "")
            m = re.search(r"abstract_id=(\d+)", href)
            if not m:
                continue
            aid = m.group(1)
            title = link.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            full_url = href if href.startswith("http") else urljoin("https://papers.ssrn.com/", href)
            if any(r.id == aid for r in records):
                continue
            records.append(
                SearchRecord(
                    source="ssrn",
                    id=aid,
                    type="paper",
                    title=title,
                    url=full_url,
                    extra={"note": "abstract via scrape; use get_record or scrape_url for text"},
                )
            )
            if len(records) >= max_results:
                break
        return records

    def get(self, record_id: str) -> SearchRecord:
        aid = record_id.replace("ssrn:", "")
        url = f"https://papers.ssrn.com/sol3/papers.cfm?abstract_id={aid}"
        html, final = fetch_page(url)
        rec = extract_readable_text(html, final)
        rec.source = "ssrn"
        rec.id = aid
        rec.type = "paper"
        return rec
