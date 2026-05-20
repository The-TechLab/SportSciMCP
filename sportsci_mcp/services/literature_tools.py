from __future__ import annotations

from sportsci_mcp.registry import get_record


def compare_papers(refs: list[str]) -> dict:
    records = []
    for ref in refs:
        if ":" not in ref:
            ref = f"pubmed:{ref}"
        records.append(get_record(ref))
    headers = ["ref", "title", "year", "population", "outcome", "limitation"]
    rows = []
    for r in records:
        rows.append(
            {
                "ref": r.ref,
                "title": r.title[:120],
                "year": r.year,
                "population": r.extra.get("population", "see abstract"),
                "outcome": r.extra.get("outcome", "see abstract"),
                "limitation": r.extra.get("limitation", "see abstract"),
                "abstract_snippet": (r.abstract or "")[:400],
            }
        )
    md_lines = [
        "| Ref | Title | Year |",
        "|-----|-------|------|",
    ]
    for r in records:
        md_lines.append(f"| `{r.ref}` | {r.title[:60]} | {r.year or 'n/a'} |")
    return {
        "count": len(records),
        "rows": rows,
        "markdown_table": "\n".join(md_lines),
        "note": "Population/outcome/limitation default to abstract — refine in chat.",
    }


def build_literature_review_outline(topic: str, refs: list[str]) -> dict:
    records = []
    for ref in refs:
        if ":" not in ref:
            ref = f"pubmed:{ref}"
        records.append(get_record(ref))
    sections = {
        "title": f"Literature review: {topic}",
        "abstract": ["Summarize scope, databases searched, and key findings."],
        "introduction": [
            f"Define the problem: {topic}",
            "State review objectives and inclusion approach.",
        ],
        "methods": [
            f"Sources synthesized: {len(records)} papers",
            "List refs: " + ", ".join(r.ref for r in records),
        ],
        "results": [f"- {r.title} ({r.ref})" for r in records],
        "discussion": [
            "Compare findings across studies",
            "Identify gaps and practical implications for sport science / clinical practice",
        ],
        "conclusion": ["Summary recommendations and future research"],
    }
    md = [f"# {sections['title']}\n"]
    for name, bullets in sections.items():
        if name == "title":
            continue
        md.append(f"\n## {name.title()}\n")
        for b in bullets:
            md.append(f"- {b}")
    return {"topic": topic, "refs": [r.ref for r in records], "outline_markdown": "\n".join(md)}
