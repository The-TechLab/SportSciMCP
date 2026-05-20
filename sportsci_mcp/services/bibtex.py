from __future__ import annotations

import re

from sportsci_mcp.registry import get_record


def _cite_key(record) -> str:
    first = (record.authors[0].split(",")[0] if record.authors else "unknown").lower()
    first = re.sub(r"[^a-z]", "", first) or "anon"
    year = record.year or "nd"
    return f"{first}{year}"


def record_to_bibtex(record) -> str:
    key = _cite_key(record)
    authors = " and ".join(record.authors) if record.authors else "Unknown"
    doi = record.doi
    return f"""@article{{{key},
  title = {{{record.title}}},
  author = {{{authors}}},
  year = {{{record.year or ""}}},
  journal = {{{record.journal or ""}}},
  doi = {{{doi or ""}}},
  url = {{{record.url}}},
  note = {{source: {record.ref}}}
}}
"""


def papers_to_bibtex(refs: list[str]) -> str:
    parts = []
    for ref in refs:
        if ":" not in ref:
            ref = f"pubmed:{ref}"
        record = get_record(ref)
        parts.append(record_to_bibtex(record))
    return "\n".join(parts)
