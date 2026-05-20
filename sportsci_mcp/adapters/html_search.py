from __future__ import annotations

import re
from abc import ABC
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup

from sportsci_mcp.adapters.base import DatasetAdapter, LiteratureAdapter
from sportsci_mcp.adapters.scrape import fetch_page, extract_readable_text
from sportsci_mcp.models import SearchRecord


class HtmlSearchMixin(ABC):
    """Shared HTML search parsing for portals without public APIs."""

    name: str
    record_type: str = "dataset"
    site_root: str = ""

    def _matches_query(self, query: str, slug: str, title: str) -> bool:
        q = query.lower()
        hay = f"{slug} {title}".lower()
        if q in hay:
            return True
        words = [w for w in q.split() if len(w) > 2]
        return bool(words) and all(w in hay for w in words)

    def _parse_links(
        self,
        html: str,
        query: str,
        *,
        max_results: int,
        href_pattern: re.Pattern[str],
        slug_group: int = 1,
        min_title_len: int = 3,
    ) -> list[SearchRecord]:
        soup = BeautifulSoup(html, "html.parser")
        records: list[SearchRecord] = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            m = href_pattern.search(href)
            if not m:
                continue
            slug = m.group(slug_group)
            if slug in {r.id for r in records}:
                continue
            title = a.get_text(strip=True)
            if len(title) < min_title_len:
                title = slug.replace("-", " ").replace("_", " ").title()
            if not self._matches_query(query, slug, title):
                continue
            full = href if href.startswith("http") else urljoin(self.site_root, href)
            records.append(
                SearchRecord(
                    source=self.name,
                    id=slug,
                    type=self.record_type,  # type: ignore[arg-type]
                    title=title,
                    url=full,
                    extra={"discovery": "html_search"},
                )
            )
            if len(records) >= max_results:
                break
        return records


class SimtkAdapter(HtmlSearchMixin, DatasetAdapter):
    name = "simtk"
    site_root = "https://simtk.org"

    def search(self, query: str, *, max_results: int = 10) -> list[SearchRecord]:
        url = f"{self.site_root}/projects/browse?search={quote_plus(query)}"
        html, _ = fetch_page(url)
        return self._parse_links(
            html,
            query,
            max_results=max_results,
            href_pattern=re.compile(r"/projects/([^/?#]+)"),
        )

    def get(self, record_id: str) -> SearchRecord:
        slug = record_id.replace("simtk:", "")
        url = f"{self.site_root}/projects/{slug}"
        html, final = fetch_page(url)
        rec = extract_readable_text(html, final)
        rec.source = "simtk"
        rec.id = slug
        rec.type = "dataset"
        return rec


class ScoreNetworkAdapter(HtmlSearchMixin, LiteratureAdapter):
    """SCORE (Sport Concussion Open Research Exchange) — HTML discovery."""

    name = "scorenetwork"
    record_type = "paper"
    site_root = "https://www.scorenetwork.org"

    def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> list[SearchRecord]:
        # Public site search / resource listings
        for path in (f"/?s={quote_plus(query)}", f"/search?q={quote_plus(query)}"):
            try:
                html, base = fetch_page(urljoin(self.site_root, path))
                hits = self._parse_links(
                    html,
                    query,
                    max_results=max_results,
                    href_pattern=re.compile(
                        r"(/resources?/[^\"'#?\s]+|/publication/[^\"'#?\s]+|/dataset/[^\"'#?\s]+)",
                        re.I,
                    ),
                    slug_group=1,
                )
                if hits:
                    return hits
            except Exception:
                continue
        html, _ = fetch_page(self.site_root)
        soup = BeautifulSoup(html, "html.parser")
        records: list[SearchRecord] = []
        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            if len(title) < 8:
                continue
            if not self._matches_query(query, a["href"], title):
                continue
            href = a["href"]
            full = href if href.startswith("http") else urljoin(self.site_root, href)
            rid = href.strip("/").replace("/", "_")[:80]
            records.append(
                SearchRecord(
                    source=self.name,
                    id=rid,
                    type="paper",
                    title=title,
                    url=full,
                )
            )
            if len(records) >= max_results:
                break
        return records

    def get(self, record_id: str) -> SearchRecord:
        rid = record_id.replace("scorenetwork:", "")
        url = rid if rid.startswith("http") else urljoin(self.site_root, rid)
        html, final = fetch_page(url)
        rec = extract_readable_text(html, final)
        rec.source = "scorenetwork"
        rec.id = rid
        rec.type = "paper"
        return rec


class MotrpacAdapter(HtmlSearchMixin, DatasetAdapter):
    name = "motrpac"
    site_root = "https://motrpac-data.org"

    def search(self, query: str, *, max_results: int = 10) -> list[SearchRecord]:
        records: list[SearchRecord] = []
        for path in ("/publications", "/data", "/"):
            try:
                html, _ = fetch_page(urljoin(self.site_root, path))
                hits = self._parse_links(
                    html,
                    query,
                    max_results=max_results,
                    href_pattern=re.compile(
                        r"(/publications/[^\"'#?\s]+|/data/[^\"'#?\s]+|/dataset/[^\"'#?\s]+)",
                        re.I,
                    ),
                )
                records.extend(hits)
            except Exception:
                continue
        # De-dupe
        seen: set[str] = set()
        out: list[SearchRecord] = []
        for r in records:
            if r.id not in seen:
                seen.add(r.id)
                out.append(r)
            if len(out) >= max_results:
                break
        return out

    def get(self, record_id: str) -> SearchRecord:
        rid = record_id.replace("motrpac:", "")
        url = rid if rid.startswith("http") else urljoin(self.site_root, rid)
        html, final = fetch_page(url)
        rec = extract_readable_text(html, final)
        rec.source = "motrpac"
        rec.id = rid
        rec.type = "dataset"
        rec.extra["program"] = "MoTrPAC - Molecular Transducers of Physical Activity"
        return rec


class MendeleyDataAdapter(HtmlSearchMixin, DatasetAdapter):
    name = "mendeley_data"
    site_root = "https://data.mendeley.com"

    def search(self, query: str, *, max_results: int = 10) -> list[SearchRecord]:
        token = __import__("os").environ.get("MENDELEY_ACCESS_TOKEN", "").strip()
        if token:
            return self._search_api(query, max_results, token)
        url = f"{self.site_root}/search?query={quote_plus(query)}"
        html, _ = fetch_page(url)
        records = self._parse_links(
            html,
            query,
            max_results=max_results,
            href_pattern=re.compile(r"/datasets/([^/?#]+)"),
        )
        if not records:
            records = self._parse_links(
                html,
                query,
                max_results=max_results,
                href_pattern=re.compile(r"research-data/[^\"']+/([^/?#\"']+)"),
            )
        return records

    def _search_api(self, query: str, max_results: int, token: str) -> list[SearchRecord]:
        import httpx

        with httpx.Client(timeout=30.0) as client:
            r = client.get(
                "https://api.mendeley.com/datasets",
                params={"query": query, "limit": max_results},
                headers={"Authorization": f"Bearer {token}"},
            )
            r.raise_for_status()
            data = r.json()
            items = data if isinstance(data, list) else data.get("items", data.get("data", []))
            out: list[SearchRecord] = []
            for item in items[:max_results]:
                did = item.get("id", "")
                out.append(
                    SearchRecord(
                        source="mendeley_data",
                        id=did,
                        type="dataset",
                        title=item.get("name") or item.get("title") or did,
                        url=f"https://data.mendeley.com/datasets/{did}",
                        abstract=(item.get("description") or "")[:2000],
                        license=str(item.get("license") or ""),
                        extra={"api": True},
                    )
                )
            return out

    def get(self, record_id: str) -> SearchRecord:
        did = record_id.replace("mendeley_data:", "")
        url = f"{self.site_root}/datasets/{did}"
        html, final = fetch_page(url)
        rec = extract_readable_text(html, final)
        rec.source = "mendeley_data"
        rec.id = did
        rec.type = "dataset"
        return rec
