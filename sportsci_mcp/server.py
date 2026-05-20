#!/usr/bin/env python3
"""
SportSciMCP — literature search, scraping, briefs, NotebookLM integration.

  python -m sportsci_mcp.server
"""

from __future__ import annotations

import json
import asyncio
from typing import Any

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from sportsci_mcp.registry import (
    get_record,
    list_sources_status,
    search_all,
    search_datasets,
    search_literature,
)
from sportsci_mcp.adapters.scrape import ScrapeAdapter
from sportsci_mcp.services.bibtex import papers_to_bibtex
from sportsci_mcp.services.briefs import format_for_notebooklm, save_brief
from sportsci_mcp.services import notebooklm as nlm
from sportsci_mcp.services.load import calc_training_load, parse_session_csv
from sportsci_mcp.services.literature_tools import build_literature_review_outline, compare_papers
from sportsci_mcp.services.norms import lookup_norms
from sportsci_mcp.services.rtp import rtp_checklist
from sportsci_mcp.services.youtube_pipeline import ingest_youtube_research

server = Server("sportsci-mcp")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="list_sources",
            description="List literature/dataset/scrape sources, enabled status, phase, and auth requirements.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="search_literature",
            description=(
                "Search papers: pubmed, openalex, ssrn, arxiv, semantic_scholar, core, "
                "scorenetwork (scrape), dimensions (API key). Enable only what you need in sources.yaml."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Any enabled literature source. Default: all active.",
                    },
                    "max_results_per_source": {"type": "integer", "default": 10},
                    "year_from": {"type": "integer"},
                    "year_to": {"type": "integer"},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="search_datasets",
            description=(
                "Search datasets: zenodo, physionet, simtk, motrpac, mendeley_data (scrape), "
                "kaggle (API key). Default: all active sources."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "zenodo, physionet, simtk, motrpac, mendeley_data, kaggle.",
                    },
                    "max_results_per_source": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="search_all",
            description=(
                "Search literature AND datasets in one call. "
                "Optional literature_sources / dataset_sources subsets."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "literature_sources": {"type": "array", "items": {"type": "string"}},
                    "dataset_sources": {"type": "array", "items": {"type": "string"}},
                    "max_results_per_source": {"type": "integer", "default": 10},
                    "year_from": {"type": "integer"},
                    "year_to": {"type": "integer"},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="ingest_youtube_research",
            description=(
                "YouTube pipeline: TranscriptMCP (yt-dlp + Whisper) → text → NotebookLM. "
                "Requires TranscriptMCP sibling repo or TRANSCRIPT_MCP_PATH."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "YouTube URL"},
                    "notebook": {"type": "string", "description": "NotebookLM alias or UUID"},
                    "title": {"type": "string"},
                    "language": {"type": "string"},
                    "wait": {"type": "boolean", "default": False},
                    "save_brief_file": {"type": "boolean", "default": False},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["url", "notebook"],
            },
        ),
        types.Tool(
            name="get_record",
            description=(
                "Fetch one paper or dataset: pubmed:, openalex:, ssrn:, arxiv:, semantic_scholar:, "
                "kaggle:owner/slug, zenodo:id, physionet:slug, url:https://..."
            ),
            inputSchema={
                "type": "object",
                "properties": {"ref": {"type": "string"}},
                "required": ["ref"],
            },
        ),
        types.Tool(
            name="scrape_url",
            description="Fetch a public web page and extract title + text (no API key).",
            inputSchema={
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        ),
        types.Tool(
            name="save_research_brief",
            description="Save a markdown research brief to the configured briefs directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ref": {"type": "string", "description": "Record ref, or omit if using url"},
                    "url": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "notes": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="papers_to_bibtex",
            description="Convert record refs or PMIDs to BibTeX.",
            inputSchema={
                "type": "object",
                "properties": {
                    "refs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "e.g. pubmed:123, openalex:W123, or bare PMID",
                    }
                },
                "required": ["refs"],
            },
        ),
        types.Tool(
            name="format_for_notebooklm",
            description="Format a record as markdown ready for NotebookLM paste or text upload.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ref": {"type": "string"},
                    "notebook_alias": {
                        "type": "string",
                        "description": "e.g. acl_rehab, ai_stem_lab",
                    },
                },
                "required": ["ref"],
            },
        ),
        types.Tool(
            name="notebooklm_list_notebooks",
            description="List NotebookLM notebook aliases from config and live nlm CLI.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="notebooklm_add_source",
            description=(
                "Add URL or text to a NotebookLM notebook via nlm CLI (uses existing nlm login)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "notebook": {
                        "type": "string",
                        "description": "Alias (acl_rehab) or notebook UUID",
                    },
                    "url": {"type": "string"},
                    "text": {"type": "string"},
                    "title": {"type": "string"},
                    "wait": {
                        "type": "boolean",
                        "default": False,
                        "description": "Wait for NotebookLM to finish processing",
                    },
                },
                "required": ["notebook"],
            },
        ),
        types.Tool(
            name="parse_session_csv",
            description="Parse GPS/sRPE/training CSV and detect columns (duration, RPE, load).",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "format_hint": {"type": "string", "default": "auto"},
                },
                "required": ["file_path"],
            },
        ),
        types.Tool(
            name="calc_training_load",
            description="Compute session load, acute/chronic load, and ACWR from sessions or CSV.",
            inputSchema={
                "type": "object",
                "properties": {
                    "csv_path": {"type": "string"},
                    "sessions": {"type": "array", "items": {"type": "object"}},
                    "acute_days": {"type": "integer", "default": 7},
                    "chronic_days": {"type": "integer", "default": 28},
                },
            },
        ),
        types.Tool(
            name="lookup_norms",
            description="Lookup curated performance norms (CMJ, sprint, Y-balance, etc.).",
            inputSchema={
                "type": "object",
                "properties": {
                    "metric": {"type": "string"},
                    "sex": {"type": "string"},
                    "sport": {"type": "string"},
                    "level": {"type": "string"},
                },
                "required": ["metric"],
            },
        ),
        types.Tool(
            name="rtp_checklist",
            description="Criterion-based return-to-play checklist (acl, hamstring, ankle_sprain).",
            inputSchema={
                "type": "object",
                "properties": {
                    "injury": {"type": "string"},
                    "phase": {
                        "type": "string",
                        "default": "return_to_play",
                        "description": "early, return_to_train, return_to_play",
                    },
                },
                "required": ["injury"],
            },
        ),
        types.Tool(
            name="compare_papers",
            description="Compare 2–5 papers by ref into a table with abstract snippets.",
            inputSchema={
                "type": "object",
                "properties": {
                    "refs": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["refs"],
            },
        ),
        types.Tool(
            name="build_literature_review_outline",
            description="IMRaD-style outline from a topic and list of paper refs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "refs": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["topic", "refs"],
            },
        ),
    ]


def _text_result(payload: Any) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=json.dumps(payload, indent=2, default=str))]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    args = arguments or {}

    if name == "list_sources":
        return _text_result(list_sources_status())

    if name == "search_literature":
        return _text_result(
            search_literature(
                args["query"],
                sources=args.get("sources"),
                max_results_per_source=args.get("max_results_per_source", 10),
                year_from=args.get("year_from"),
                year_to=args.get("year_to"),
            )
        )

    if name == "search_datasets":
        return _text_result(
            search_datasets(
                args["query"],
                sources=args.get("sources"),
                max_results_per_source=args.get("max_results_per_source", 10),
            )
        )

    if name == "search_all":
        return _text_result(
            search_all(
                args["query"],
                literature_sources=args.get("literature_sources"),
                dataset_sources=args.get("dataset_sources"),
                max_results_per_source=args.get("max_results_per_source", 10),
                year_from=args.get("year_from"),
                year_to=args.get("year_to"),
            )
        )

    if name == "ingest_youtube_research":
        return _text_result(
            ingest_youtube_research(
                args["url"],
                args["notebook"],
                title=args.get("title"),
                language=args.get("language"),
                wait=bool(args.get("wait")),
                save_brief_file=bool(args.get("save_brief_file")),
                tags=args.get("tags"),
            )
        )

    if name == "get_record":
        rec = get_record(args["ref"])
        return _text_result(rec.to_dict())

    if name == "scrape_url":
        rec = ScrapeAdapter().fetch(args["url"])
        return _text_result(rec.to_dict())

    if name == "save_research_brief":
        if args.get("ref"):
            rec = get_record(args["ref"])
        elif args.get("url"):
            rec = ScrapeAdapter().fetch(args["url"])
        else:
            raise ValueError("Provide ref or url")
        return _text_result(
            save_brief(rec, tags=args.get("tags"), notes=args.get("notes", ""))
        )

    if name == "papers_to_bibtex":
        return _text_result({"bibtex": papers_to_bibtex(args["refs"])})

    if name == "format_for_notebooklm":
        rec = get_record(args["ref"])
        md = format_for_notebooklm(rec, notebook_alias=args.get("notebook_alias", ""))
        return _text_result({"markdown": md, "ref": rec.ref})

    if name == "notebooklm_list_notebooks":
        return _text_result(nlm.list_notebooks())

    if name == "notebooklm_add_source":
        if not args.get("url") and not args.get("text"):
            raise ValueError("Provide url or text")
        return _text_result(
            nlm.add_source(
                args["notebook"],
                url=args.get("url"),
                text=args.get("text"),
                title=args.get("title"),
                wait=bool(args.get("wait")),
            )
        )

    if name == "parse_session_csv":
        return _text_result(parse_session_csv(args["file_path"], args.get("format_hint", "auto")))

    if name == "calc_training_load":
        return _text_result(
            calc_training_load(
                args.get("sessions"),
                csv_path=args.get("csv_path"),
                acute_days=args.get("acute_days", 7),
                chronic_days=args.get("chronic_days", 28),
            )
        )

    if name == "lookup_norms":
        return _text_result(
            lookup_norms(
                args["metric"],
                sex=args.get("sex"),
                sport=args.get("sport"),
                level=args.get("level"),
            )
        )

    if name == "rtp_checklist":
        return _text_result(rtp_checklist(args["injury"], args.get("phase", "return_to_play")))

    if name == "compare_papers":
        return _text_result(compare_papers(args["refs"]))

    if name == "build_literature_review_outline":
        return _text_result(build_literature_review_outline(args["topic"], args["refs"]))

    raise ValueError(f"Unknown tool: {name}")


async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
