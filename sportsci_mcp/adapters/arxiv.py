from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from sportsci_mcp.adapters.base import LiteratureAdapter
from sportsci_mcp.models import SearchRecord

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


class ArxivAdapter(LiteratureAdapter):
    name = "arxiv"
    API = "https://export.arxiv.org/api/query"

    def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> list[SearchRecord]:
        q = f"all:{query}"
        if year_from:
            q += f" AND submittedDate:[{year_from}01010000 TO "
            end = year_to if year_to else 2099
            q += f"{end}12312359]"
        params = {"search_query": q, "start": 0, "max_results": max_results}
        with httpx.Client(timeout=45.0) as client:
            r = client.get(self.API, params=params)
            r.raise_for_status()
            return self._parse_feed(r.text)

    def get(self, record_id: str) -> SearchRecord:
        aid = record_id.replace("arxiv:", "").split("v")[0]
        params = {"id_list": aid}
        with httpx.Client(timeout=45.0) as client:
            r = client.get(self.API, params=params)
            r.raise_for_status()
            records = self._parse_feed(r.text)
            if not records:
                raise ValueError(f"arXiv not found: {aid}")
            return records[0]

    def _parse_feed(self, xml_text: str) -> list[SearchRecord]:
        root = ET.fromstring(xml_text)
        records: list[SearchRecord] = []
        for entry in root.findall("atom:entry", ATOM_NS):
            raw_id = self._text(entry.find("atom:id", ATOM_NS))
            arxiv_id = raw_id.rsplit("/abs/", 1)[-1] if raw_id else ""
            title = self._text(entry.find("atom:title", ATOM_NS)).replace("\n", " ")
            abstract = self._text(entry.find("atom:summary", ATOM_NS)).replace("\n", " ")
            authors = [
                self._text(a.find("atom:name", ATOM_NS))
                for a in entry.findall("atom:author", ATOM_NS)
            ]
            published = self._text(entry.find("atom:published", ATOM_NS))
            year = int(published[:4]) if published and len(published) >= 4 else None
            pdf_link = ""
            for link in entry.findall("atom:link", ATOM_NS):
                if link.attrib.get("title") == "pdf":
                    pdf_link = link.attrib.get("href", "")
            records.append(
                SearchRecord(
                    source="arxiv",
                    id=arxiv_id,
                    type="paper",
                    title=title,
                    url=raw_id or f"https://arxiv.org/abs/{arxiv_id}",
                    abstract=abstract,
                    authors=authors,
                    year=year,
                    journal="arXiv",
                    extra={"pdf_url": pdf_link},
                )
            )
        return records

    @staticmethod
    def _text(node: ET.Element | None) -> str:
        if node is None:
            return ""
        return (node.text or "").strip()
