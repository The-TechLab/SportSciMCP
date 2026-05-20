# SportSciMCP

**v0.4** · Your sports-science research desk inside any AI assistant.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-compatible-purple.svg)](https://modelcontextprotocol.io)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-green.svg)](https://www.python.org/)

SportSciMCP is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server for **research, performance, and injury science**. Search literature and datasets across PubMed, OSF, Figshare, PhysioNet, Kaggle, and more — run training-load analysis, RTP checklists, and pipe YouTube lectures into NotebookLM — all from one conversation.

Works with **Cursor**, **Claude Desktop**, **Gemini**, **GitHub Copilot**, **OpenAI Codex**, and **Cursor Agent**.

> **Pick what you use.** Enable sources in `config/sources.yaml`. Add API keys only for the services you turn on. Everything else keeps working.

**Repository:** https://github.com/The-TechLab/SportSciMCP

---

## Table of contents

- [Why SportSciMCP?](#why-sportscimcp)
- [Compatible AI clients](#compatible-ai-clients)
- [Quick start](#quick-start)
- [Sources at a glance](#sources-at-a-glance)
- [API keys](#api-keys)
- [Tools](#tools)
- [Sample prompts](#sample-prompts)
- [YouTube → TranscriptMCP → NotebookLM](#youtube--transcriptmcp--notebooklm)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Contributing](#contributing)

---

## Why SportSciMCP?

| Without it | With SportSciMCP |
|------------|------------------|
| Tab-hopping PubMed, OSF, Zenodo, Kaggle | `search_all` — one prompt, many sources |
| Manual abstract copy-paste | `save_research_brief` → markdown on disk |
| Guesswork on return-to-play | `rtp_checklist` (ACL, hamstring, ankle) |
| Spreadsheet load math by hand | `parse_session_csv` + `calc_training_load` (ACWR) |
| YouTube lecture → notes by hand | `ingest_youtube_research` → transcript → NotebookLM |

---

## Compatible AI clients

SportSciMCP uses MCP over **stdio**. Configure once per client:

| Client | Config location |
|--------|-----------------|
| **Cursor** / **Cursor Agent** | `~/.cursor/mcp.json` |
| **Claude Desktop** | `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) |
| **Gemini** | MCP-capable Gemini tooling that accepts stdio servers |
| **GitHub Copilot** | VS Code MCP settings (when enabled) |
| **OpenAI Codex** | Agent / IDE MCP server list |

```json
{
  "mcpServers": {
    "sportsci": {
      "command": "/path/to/.cursor/mcp-wrappers/sportscience.sh",
      "args": []
    }
  }
}
```

Restart your client after adding the server.

---

## Quick start

### 1. Clone & install

```bash
git clone https://github.com/The-TechLab/SportSciMCP.git
cd SportSciMCP

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Optional — API keys

```bash
cp config/secrets.example.env ~/.cursor/mcp-secrets.env
# Edit: uncomment only the keys you need
```

### 3. Wrapper script (Cursor example)

`~/.cursor/mcp-wrappers/sportscience.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
if [[ -f "$HOME/.cursor/mcp-secrets.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$HOME/.cursor/mcp-secrets.env"
  set +a
fi
export PYTHONPATH="/absolute/path/to/SportSciMCP${PYTHONPATH:+:$PYTHONPATH}"
exec /absolute/path/to/SportSciMCP/.venv/bin/python -m sportsci_mcp.server
```

```bash
chmod +x ~/.cursor/mcp-wrappers/sportscience.sh
```

### 4. Verify

> *"Use SportSciMCP `list_sources` — which sources are active?"*

---

## Sources at a glance

### Literature (papers & preprints)

| Source | Site | Key? |
|--------|------|------|
| pubmed | [PubMed](https://pubmed.ncbi.nlm.nih.gov) | No |
| openalex | [OpenAlex](https://openalex.org) | No |
| ssrn | [SSRN](https://www.ssrn.com) | No (HTML search) |
| arxiv | [arXiv](https://arxiv.org) | No |
| semantic_scholar | [Semantic Scholar](https://www.semanticscholar.org) | Optional |
| core | [CORE](https://core.ac.uk) | Optional |
| dimensions | [Dimensions.ai](https://app.dimensions.ai) | **Required** |
| scorenetwork | [SCORE Network](https://www.scorenetwork.org) | No (HTML) |
| osf | [OSF](https://osf.io) | No |
| sportdiscus | [SPORTDiscus](https://www.ebsco.com/products/research-databases/sportdiscus) | **EBSCO** (institutional) |

### Datasets

| Source | Site | Key? |
|--------|------|------|
| zenodo | [Zenodo](https://zenodo.org) | No |
| physionet | [PhysioNet](https://physionet.org) | No |
| figshare | [Figshare](https://figshare.com) | No |
| simtk | [SimTK](https://simtk.org) | No (HTML) |
| motrpac | [MoTrPAC](https://motrpac-data.org) | No (HTML) |
| mendeley_data | [Mendeley Data](https://data.mendeley.com) | Optional |
| kaggle | [Kaggle](https://www.kaggle.com) | **Required** |

### Other

| Tool | Purpose |
|------|---------|
| scrape_url | Any public web page → title + text |

Disable any row in `config/sources.yaml` with `enabled: false`.

---

## API keys

### None needed (13+ sources work immediately)

PubMed, OpenAlex, SSRN, arXiv, CORE (no key), OSF, Figshare, PhysioNet, SimTK, MoTrPAC, SCORE Network, Zenodo, and generic `scrape_url`.

Optional politeness env vars: `PUBMED_EMAIL`, `OPENALEX_EMAIL`

### Optional (better limits)

| Variable | Where to get it |
|----------|-----------------|
| `CORE_API_KEY` | [core.ac.uk/api-keys/register](https://core.ac.uk/api-keys/register) |
| `SEMANTIC_SCHOLAR_API_KEY` | [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api) |
| `MENDELEY_ACCESS_TOKEN` | [dev.mendeley.com](https://dev.mendeley.com/) |

### Required only if you use that source

| Variables | Source |
|-----------|--------|
| `DIMENSIONS_API_KEY` | Dimensions.ai |
| `KAGGLE_USERNAME` + `KAGGLE_KEY` | Kaggle → Settings → API |
| `EBSCO_USER_ID` + `EBSCO_PASSWORD` | Your university library (SPORTDiscus) |
| `EBSCO_PROFILE` | Optional; default `eds` |

Missing keys → source is **skipped** with a clear message in `list_sources`. No crash, no blocking other sources.

### TranscriptMCP (YouTube pipeline only)

| Variable | Purpose |
|----------|---------|
| `TRANSCRIPT_MCP_PATH` | Path to [TranscriptMCP](https://github.com/The-TechLab/TranscriptMCP) if not cloned as `../TranscriptMCP` |

Template: `config/secrets.example.env`

---

## Tools

### Discovery

| Tool | What it does |
|------|----------------|
| `list_sources` | Show active sources, phases, credential status |
| `search_literature` | Papers across enabled literature sources |
| `search_datasets` | Datasets across enabled dataset sources |
| **`search_all`** | **Literature + datasets in one call** |
| `get_record` | Fetch one item (`pubmed:123`, `osf:abc`, `figshare:99`, …) |
| `scrape_url` | Public URL → extracted text |

### Research workflow

| Tool | What it does |
|------|----------------|
| `save_research_brief` | Markdown brief on disk |
| `papers_to_bibtex` | Refs → BibTeX |
| `format_for_notebooklm` | Notebook-ready markdown |
| `compare_papers` | Comparison table (2–5 papers) |
| `build_literature_review_outline` | IMRaD outline from topic + refs |

### Applied sports science

| Tool | What it does |
|------|----------------|
| `parse_session_csv` | Parse GPS / sRPE / load CSV |
| `calc_training_load` | Load, acute/chronic, **ACWR**, spike flags |
| `lookup_norms` | CMJ, sprint, Y-balance ([`data/norms.yaml`](sportsci_mcp/data/norms.yaml)) |
| `rtp_checklist` | ACL, hamstring, ankle ([`data/rtp/`](sportsci_mcp/data/rtp/)) |

### NotebookLM & YouTube

| Tool | What it does |
|------|----------------|
| `notebooklm_list_notebooks` | Aliases from config + live `nlm` list |
| `notebooklm_add_source` | Add URL or text via `nlm` CLI |
| **`ingest_youtube_research`** | **YouTube → TranscriptMCP → NotebookLM** |

Requires `nlm login` for NotebookLM tools. See [YouTube pipeline](#youtube--transcriptmcp--notebooklm) below.

---

## Sample prompts

Copy into Cursor, Claude, Gemini, Copilot, or Codex.

### Unified search

```
search_all for "ACL return to sport" — literature and datasets,
max 5 per source. Use pubmed, openalex, osf, zenodo, figshare.
```

```
search_all on hamstring injury prevention since 2020.
```

### Literature

```
Search literature on concussion using pubmed, core, and scorenetwork.
Save briefs for the top 5 results.
```

```
Compare pubmed:38123456 and openalex:W123 — table and evidence gaps.
```

```
Build a literature review outline on Nordic hamstring programs
using these refs: [paste refs].
```

### Datasets

```
Search datasets for GPS football tracking on zenodo, figshare, and physionet.
```

```
Find exercise omics data on motrpac and kaggle for endurance training.
```

### Clinical & performance

```
RTP checklist for ACL, phase return_to_play.
```

```
Lookup norms for cmj_height_cm — female, soccer, collegiate.
```

```
Parse ~/data/team_srpe.csv and calculate ACWR (7-day acute, 28-day chronic).
```

### NotebookLM & web

```
Format pubmed:36234567 for NotebookLM and add to acl_rehab.
```

```
Scrape https://example.com/guideline and save a brief tagged rtp.
```

### Admin

```
list_sources — show active sources and which need API keys.
```

---

## YouTube → TranscriptMCP → NotebookLM

The **`ingest_youtube_research`** tool runs a full pipeline:

```
YouTube URL
    → TranscriptMCP (yt-dlp + Whisper)
    → formatted markdown
    → NotebookLM (nlm source add)
    → optional research brief on disk
```

### Prerequisites

1. **[TranscriptMCP](https://github.com/The-TechLab/TranscriptMCP)** cloned beside SportSciMCP:
   ```
   MCP Servers/
   ├── SportSciMCP/
   └── TranscriptMCP/
   ```
2. TranscriptMCP dependencies installed (`yt-dlp`, `faster-whisper`, `ffmpeg`)
3. **`nlm login`** for NotebookLM
4. Notebook alias in `config/notebooks.yaml` (e.g. `acl_rehab`)

### Example prompt

```
Ingest this YouTube lecture into acl_rehab:
https://www.youtube.com/watch?v=VIDEO_ID
Save a brief tagged youtube.
```

### What you get back

- Transcript preview + length  
- NotebookLM add status  
- Optional brief file path  

---

## Configuration

| File | Purpose |
|------|---------|
| `config/sources.yaml` | Enable/disable each source |
| `config/notebooks.yaml` | NotebookLM notebook aliases → UUIDs |
| `config/secrets.example.env` | API key template |
| `sportsci_mcp/data/norms.yaml` | Performance norms (edit for your lab) |
| `sportsci_mcp/data/rtp/*.yaml` | RTP checklists (edit with your protocol) |

Example — turn off Kaggle:

```yaml
datasets:
  kaggle:
    enabled: false
```

Example — custom briefs folder:

```bash
export SPORTSCI_BRIEFS_DIR=~/research/briefs
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  AI client (Cursor · Claude · Gemini · Copilot · Codex) │
└─────────────────────────┬───────────────────────────────┘
                          │ MCP stdio
┌─────────────────────────▼───────────────────────────────┐
│  SportSciMCP tools (search, load, RTP, YouTube, …)      │
└─────────────────────────┬───────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
   Literature         Datasets      Services
   adapters           adapters      (load, rtp, nlm)
   pubmed·osf·…       zenodo·…      youtube_pipeline
        │                 │
        ▼                 ▼
   Public APIs      HTML scrape (ethical, no paywalls)
```

- **Pluggable adapters** — add a file under `sportsci_mcp/adapters/`
- **Unified records** — same JSON shape for papers and datasets
- **Fail soft** — missing credentials skip that source only

Roadmap: [docs/ROADMAP.md](docs/ROADMAP.md) · Coming: **athleteOS** API (Phase 5)

---

## Project layout

```
SportSciMCP/
├── config/
│   ├── sources.yaml
│   ├── notebooks.yaml
│   └── secrets.example.env
├── sportsci_mcp/
│   ├── adapters/          # pubmed, osf, figshare, kaggle, …
│   ├── services/          # load, norms, rtp, notebooklm, youtube_pipeline
│   ├── data/              # norms + RTP YAML
│   └── server.py
├── docs/ROADMAP.md
└── pyproject.toml
```

Run locally: `python -m sportsci_mcp.server`

---

## Contributing

PRs welcome for:

- New **source adapters** (see `sportsci_mcp/adapters/base.py`)
- Expanded **norms** and **RTP** YAML
- Bug fixes on HTML-scrape sources (site layout changes)

Keep new sources **opt-in** via `config/sources.yaml`.

---

## License

MIT © [The Tech Lab](https://github.com/The-TechLab)

---

<p align="center">
  <strong>Built for researchers, clinicians, and performance staff who live in the data.</strong><br>
  Enable what you need · Ignore the rest · Ship the science
</p>
