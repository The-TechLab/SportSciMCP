# SportSciMCP

**Your sports-science research desk inside any AI assistant.**

SportSciMCP is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server built for people who work at the intersection of **research, performance, and injury science**. It connects your AI tools to PubMed, open datasets, biomechanics repositories, training-load spreadsheets, return-to-play checklists, and Google NotebookLM — without opening fifteen browser tabs.

Use it in **Cursor**, **Claude Desktop**, **Gemini**, **GitHub Copilot**, **OpenAI Codex**, or any client that supports MCP. You talk in plain English; the server runs the searches, parsing, and formatting.

> **You do not need every API key.** Enable only the sources you want in `config/sources.yaml` and add keys only for those services.

---

## What problem does this solve?

| Without SportSciMCP | With SportSciMCP |
|---------------------|------------------|
| Manual PubMed + dataset hunting | One prompt across many sources |
| Copy-pasting abstracts into notes | `save_research_brief` → markdown on disk |
| Guessing RTP criteria | `rtp_checklist` from curated YAML |
| sRPE spreadsheets by hand | `parse_session_csv` + `calc_training_load` (ACWR) |
| Feeding NotebookLM one link at a time | `notebooklm_add_source` via `nlm` CLI |

---

## Compatible AI clients

SportSciMCP speaks standard MCP over **stdio**. Wire it once; use it anywhere your client supports custom MCP servers:

| Client | How to connect |
|--------|----------------|
| **Cursor** | `~/.cursor/mcp.json` + wrapper script (below) |
| **Claude Desktop** | `claude_desktop_config.json` → `mcpServers` |
| **Gemini** | MCP-compatible Gemini tooling / extensions that accept stdio servers |
| **GitHub Copilot** | VS Code MCP configuration (when MCP servers are enabled) |
| **OpenAI Codex** | MCP server entry in your agent environment |
| **Cursor Agent / Cloud** | Same MCP config as Cursor desktop |

Example MCP entry (adjust paths):

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

---

## Quick start

### 1. Clone and install

```bash
git clone https://github.com/The-TechLab/SportSciMCP.git
cd SportSciMCP

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

### 2. (Optional) API keys

Only add keys for sources you will use. Copy the template:

```bash
mkdir -p ~/.cursor
cp config/secrets.example.env ~/.cursor/mcp-secrets.env
# Edit and uncomment the keys you need
```

### 3. Cursor wrapper (recommended)

Create `~/.cursor/mcp-wrappers/sportscience.sh`:

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
exec /absolute/path/to/.venv/bin/python -m sportsci_mcp.server
```

```bash
chmod +x ~/.cursor/mcp-wrappers/sportscience.sh
```

Add to `~/.cursor/mcp.json` (see table above), then **restart Cursor**.

### 4. Verify

Ask your agent:

> *"Use SportSciMCP list_sources and tell me which sources are active."*

---

## API keys — what you need (and what you don't)

### No key required (works out of the box)

| Source | Type | Best for |
|--------|------|----------|
| **pubmed** | Literature | Peer-reviewed biomedical papers |
| **openalex** | Literature | Broad scholarly metadata + open access links |
| **ssrn** | Literature | Working papers (HTML search) |
| **arxiv** | Literature | Preprints (ML, methods, theory) |
| **core** | Literature | Open-access full-text aggregation ([core.ac.uk](https://core.ac.uk)) |
| **scorenetwork** | Literature | Concussion / SCORE resources ([scorenetwork.org](https://www.scorenetwork.org)) |
| **zenodo** | Datasets | General research datasets |
| **physionet** | Datasets | Physiology & biomedical signals ([physionet.org](https://physionet.org)) |
| **simtk** | Datasets | Biomechanics simulation projects ([simtk.org](https://simtk.org)) |
| **motrpac** | Datasets | Exercise omics ([motrpac-data.org](https://motrpac-data.org)) |
| **mendeley_data** | Datasets | Shared datasets ([data.mendeley.com](https://data.mendeley.com)) — HTML search |
| **scrape_url** | Web | Any public guideline or article page |

Optional env vars (polite pools, not required): `PUBMED_EMAIL`, `OPENALEX_EMAIL`

---

### Optional keys (better limits or richer data)

| Variable | Source | Get a key | Why bother? |
|----------|--------|-----------|-------------|
| `CORE_API_KEY` | CORE | [core.ac.uk/api-keys/register](https://core.ac.uk/api-keys/register) | Higher rate limits, full-text access |
| `SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar | [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api) | Avoid 429 rate limits on heavy use |
| `MENDELEY_ACCESS_TOKEN` | Mendeley Data | [dev.mendeley.com](https://dev.mendeley.com/) | API search instead of HTML scrape |

---

### Required keys (only if you enable that source)

| Variable | Source | Get a key |
|----------|--------|-----------|
| `DIMENSIONS_API_KEY` | [Dimensions.ai](https://app.dimensions.ai) | Dimensions account → API access |
| `KAGGLE_USERNAME` + `KAGGLE_KEY` | [Kaggle](https://www.kaggle.com) | Account → Settings → API → Create token |

If these are missing, SportSciMCP **skips** those sources and tells you why in `list_sources` — everything else still works.

---

### Pick your stack (`config/sources.yaml`)

Turn off anything you do not need:

```yaml
datasets:
  kaggle:
    enabled: false   # ← no Kaggle? disable here.
```

Set `enabled: false` — no code changes required.

---

## Tools reference

### Discovery & records

| Tool | Description |
|------|-------------|
| `list_sources` | Active sources, phases, credential status |
| `search_literature` | Papers across enabled literature adapters |
| `search_datasets` | Datasets across Zenodo, PhysioNet, SimTK, MoTrPAC, Mendeley, Kaggle, … |
| `get_record` | One item by ref (`pubmed:123`, `kaggle:owner/slug`, `core:456`, …) |
| `scrape_url` | Fetch a public URL → title + text (no API key) |

### Research workflow

| Tool | Description |
|------|-------------|
| `save_research_brief` | Save markdown brief (default: `~/QAI-Lab-Drive/research-briefs/`) |
| `papers_to_bibtex` | PMIDs / refs → BibTeX |
| `format_for_notebooklm` | Notebook-ready markdown |
| `compare_papers` | Side-by-side table for 2–5 papers |
| `build_literature_review_outline` | IMRaD outline from a topic + refs |

### Applied sports science (Phase 3)

| Tool | Description |
|------|-------------|
| `parse_session_csv` | Parse GPS / sRPE / load CSV files |
| `calc_training_load` | Session load, acute/chronic load, **ACWR**, spike flags |
| `lookup_norms` | CMJ, sprint, Y-balance (`sportsci_mcp/data/norms.yaml`) |
| `rtp_checklist` | ACL, hamstring, ankle (`sportsci_mcp/data/rtp/`) |

### NotebookLM (uses your existing `nlm login`)

| Tool | Description |
|------|-------------|
| `notebooklm_list_notebooks` | Config aliases + live notebook list |
| `notebooklm_add_source` | Add URL or text to a notebook |

Notebook aliases live in `config/notebooks.yaml` (e.g. `acl_rehab`, `ai_stem_lab`).

---

## Sample prompts (copy into any MCP client)

### Literature reviews

- *"Search literature on **ACL return-to-sport criteria** using PubMed, OpenAlex, and CORE since 2019. Save briefs for the top 5."*
- *"Find **hamstring injury prevention** papers on arXiv and Semantic Scholar, then build a literature review outline."*
- *"Compare these papers: pubmed:38123456, openalex:W1234567890 — table plus gaps for discussion."*

### Datasets & methods

- *"Search datasets for **GPS football tracking** on Zenodo, Kaggle, and PhysioNet."*
- *"Find **exercise genomics** data on MoTrPAC and Mendeley Data."*
- *"Search SimTK for **OpenSim gait** projects."*

### Clinical / performance

- *"Give me the **ACL return_to_play** RTP checklist from SportSciMCP."*
- *"Lookup norms for **cmj_height_cm**, female, soccer, collegiate."*
- *"Parse `~/data/team_srpe.csv` and calculate **ACWR** with 7-day acute and 28-day chronic windows."*

### Web + NotebookLM

- *"Scrape this guideline URL and save a research brief tagged `rtp`."*
- *"Get pubmed:36234567, format for NotebookLM, and add to **acl_rehab**."*
- *"List my NotebookLM notebook aliases and add this paper URL to QAI Lab."*

### Admin

- *"Run `list_sources` and show which need API keys."*
- *"Search literature on concussion from **scorenetwork** and CORE only."*

---

## Architecture (30-second version)

```
Your AI (Cursor, Claude, Gemini, Copilot, Codex, …)
        ↓ MCP stdio
   SportSciMCP tools
        ↓
   Source adapters (pubmed, zenodo, core, …)
        ↓
   Public APIs + ethical HTML scrape
```

- **Pluggable sources** — one file per site in `sportsci_mcp/adapters/`
- **Unified record shape** — papers and datasets return the same JSON structure
- **Fail soft** — missing keys skip that source; others keep running

See [docs/ROADMAP.md](docs/ROADMAP.md) for phase history and future plans.

---

## Project layout

```
SportSciMCP/
├── config/
│   ├── sources.yaml          # Enable/disable sources
│   ├── notebooks.yaml        # NotebookLM aliases
│   └── secrets.example.env   # API key template
├── sportsci_mcp/
│   ├── adapters/             # pubmed, core, kaggle, …
│   ├── services/             # load, norms, rtp, notebooklm
│   ├── data/                 # norms + RTP YAML (editable)
│   └── server.py             # MCP entrypoint
├── docs/ROADMAP.md
└── pyproject.toml
```

Run manually: `python -m sportsci_mcp.server`

---

## Contributing

PRs welcome — especially new **adapters** (follow `sportsci_mcp/adapters/base.py`) and expanded **norms/RTP** YAML. Keep sources opt-in via `config/sources.yaml`.

---

## License

MIT © [The Tech Lab](https://github.com/The-TechLab)

---

<p align="center">
  <strong>Built for researchers, clinicians, and performance staff who live in the data.</strong><br>
  Enable what you need. Ignore the rest. Ship the science.
</p>
