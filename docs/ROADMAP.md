# SportSciMCP roadmap

## Phase 1 — done
Literature (PubMed, OpenAlex, SSRN scrape), scrape_url, briefs, BibTeX, NotebookLM.

## Phase 2 — done (v0.2)
arXiv, Semantic Scholar, CORE, Dimensions*, Zenodo, PhysioNet, Kaggle*, SimTK, MoTrPAC, Mendeley Data, SCORE Network.

\* API key required when `requires_auth: true` in `config/sources.yaml`.

## Phase 3 — done (v0.3)
Applied sports science tools + extended source catalog.

### Tools
| Tool | Purpose |
|------|---------|
| `parse_session_csv` | GPS / sRPE / load CSV |
| `calc_training_load` | Load, ACWR, spike flags |
| `lookup_norms` | CMJ, sprint, Y-balance (`data/norms.yaml`) |
| `rtp_checklist` | ACL, hamstring, ankle (`data/rtp/`) |
| `compare_papers` | Side-by-side paper table |
| `build_literature_review_outline` | IMRaD outline from refs |

### Sources added in v0.3
| Source | Type | Auth |
|--------|------|------|
| core.ac.uk | literature | Optional `CORE_API_KEY` |
| dimensions.ai | literature | `DIMENSIONS_API_KEY` required |
| scorenetwork.org | literature | Scrape |
| simtk.org | datasets | Scrape |
| motrpac-data.org | datasets | Scrape |
| data.mendeley.com | datasets | Scrape; optional `MENDELEY_ACCESS_TOKEN` |
| physionet.org | datasets | Already in v0.2 |

### Pick what you use
Edit `config/sources.yaml` → `enabled: false` on any source you do not need.

## Phase 4 — future
- athleteOS API
- `search_all` convenience tool
- OSF, Figshare, SPORTDiscus (institutional)
- YouTube → TranscriptMCP → NotebookLM pipeline helper
