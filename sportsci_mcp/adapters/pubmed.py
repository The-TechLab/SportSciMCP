from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET

import httpx

from sportsci_mcp.adapters.base import LiteratureAdapter
from sportsci_mcp.config import pubmed_email
from sportsci_mcp.models import SearchRecord

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubMedAdapter(LiteratureAdapter):
    name = "pubmed"

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=30.0,
            headers={"User-Agent": f"SportSciMCP ({pubmed_email()})"},
        )

    def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> list[SearchRecord]:
        term = query
        if year_from:
            term += f" AND {year_from}[pdat]"
        if year_to:
            term += f" AND {year_to}[pdat]"
        params = {
            "db": "pubmed",
            "term": term,
            "retmax": max_results,
            "retmode": "json",
            "email": pubmed_email(),
        }
        with self._client() as client:
            r = client.get(f"{EUTILS}/esearch.fcgi", params=params)
            r.raise_for_status()
            ids = r.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return []
            return self._fetch_summaries(client, ids)

    def _fetch_summaries(self, client: httpx.Client, pmids: list[str]) -> list[SearchRecord]:
        r = client.get(
            f"{EUTILS}/esummary.fcgi",
            params={
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "json",
                "email": pubmed_email(),
            },
        )
        r.raise_for_status()
        result = r.json().get("result", {})
        records: list[SearchRecord] = []
        for pmid in pmids:
            if pmid == "uids":
                continue
            item = result.get(pmid, {})
            authors = [
                a.get("name", "")
                for a in item.get("authors", [])
                if isinstance(a, dict)
            ]
            pubdate = item.get("pubdate", "") or ""
            year_match = re.search(r"\d{4}", pubdate)
            year = int(year_match.group()) if year_match else None
            records.append(
                SearchRecord(
                    source="pubmed",
                    id=pmid,
                    type="paper",
                    title=item.get("title", "Untitled"),
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    abstract="",
                    authors=authors,
                    year=year,
                    journal=item.get("fulljournalname") or item.get("source", ""),
                    doi=self._extract_doi(item.get("elocationid", "")),
                    extra={"pubdate": pubdate},
                )
            )
        return records

    def get(self, record_id: str) -> SearchRecord:
        pmid = record_id.replace("pubmed:", "")
        params = {
            "db": "pubmed",
            "id": pmid,
            "retmode": "xml",
            "email": pubmed_email(),
        }
        with self._client() as client:
            r = client.get(f"{EUTILS}/efetch.fcgi", params=params)
            r.raise_for_status()
            return self._parse_article_xml(pmid, r.text)

    def _parse_article_xml(self, pmid: str, xml_text: str) -> SearchRecord:
        root = ET.fromstring(xml_text)
        article = root.find(".//PubmedArticle")
        if article is None:
            raise ValueError(f"PubMed article not found: {pmid}")
        medline = article.find(".//MedlineCitation")
        art = medline.find("Article") if medline is not None else None
        title = self._text(art.find("ArticleTitle")) if art is not None else "Untitled"
        abstract_parts = art.findall(".//AbstractText") if art is not None else []
        abstract = " ".join(self._text(a) for a in abstract_parts if self._text(a))
        authors = []
        if art is not None:
            for au in art.findall(".//Author"):
                last = self._text(au.find("LastName"))
                fore = self._text(au.find("ForeName"))
                if last:
                    authors.append(f"{last}, {fore}".strip(", "))
        journal_node = medline.find(".//Journal/Title") if medline is not None else None
        journal = self._text(journal_node)
        year_node = medline.find(".//PubDate/Year") if medline is not None else None
        year = int(self._text(year_node)) if self._text(year_node).isdigit() else None
        doi = ""
        for id_node in article.findall(".//ArticleId"):
            if id_node.attrib.get("IdType") == "doi":
                doi = self._text(id_node)
        return SearchRecord(
            source="pubmed",
            id=pmid,
            type="paper",
            title=title,
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            abstract=abstract,
            authors=authors,
            year=year,
            journal=journal,
            doi=doi,
        )

    @staticmethod
    def _text(node: ET.Element | None) -> str:
        if node is None:
            return ""
        return "".join(node.itertext()).strip()

    @staticmethod
    def _extract_doi(elocation: str) -> str:
        if "doi" in elocation.lower():
            return elocation.split()[-1]
        return ""
