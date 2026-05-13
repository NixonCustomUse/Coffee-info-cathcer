# Coffee Info Catcher — Agent Guide

## Data flow

```
sources.json → coffee_radar.py → data/items.jsonl
                                     ↓
                               coffee_ai.py → data/items.enriched.jsonl
                                                  ↓
                                            coffee_notion_sync.py → Notion
                                                  ↓  (Monday only)
                                            coffee_weekly.py → reports/weekly/
```

## Package structure (after restructure)

```
coffee/                  # Package, 6 submodules
  util.py                # clean_text, parse_date, normalize_url, fetch_*, JSONL I/O, strip_feed_boilerplate
  sources.py             # Source dataclass + load_sources()
  parsers.py             # parse_feed/page/crossref/europe_pmc + LinkExtractor
  classify.py            # Item dataclass, CATEGORY_KEYWORDS, classify(), scoring, segment defs
  report.py              # Markdown report generation
  __init__.py            # Re-exports
coffee_radar.py          # Thinner: collect() + main() + CLI only
coffee_ai.py             # Deterministic Chinese summaries only (no LLM)
coffee_weekly.py         # Weekly article generation (fallback only)
coffee_notion_sync.py    # Notion sync with SQLite dedup
generate_html.py         # HTML dashboard from JSONL
```

## Pipeline (run order matters)

```bash
./run_daily_sync.sh
# 1. coffee_radar.py --days 45 --limit 30 --min-score 2  → data/items.jsonl
# 2. coffee_ai.py --input data/items.jsonl               → data/items.enriched.jsonl
# 3. coffee_notion_sync.py --items data/items.enriched.jsonl --limit 30
```

Weekly report auto-generates on Monday (`$(date +%u)` = 1). Manual: `python3 coffee_weekly.py --input data/items.enriched.jsonl`

## Key env vars

| Var | Notes |
|-----|-------|
| `NOTION_TOKEN` | Required for Notion sync. Use `--skip-notion-if-unconfigured` to pass. |
| `NOTION_ARTICLES_DATABASE_ID` | Env var overrides `notion_config.json` |

## Focused commands

```bash
# Collect only
python3 coffee_radar.py --days 30 --limit 20 --min-score 3

# Enrich only
python3 coffee_ai.py --input data/items.jsonl

# Notion dry run
python3 coffee_notion_sync.py --items data/items.enriched.jsonl --dry-run

# Run all tests
python3 -m unittest discover -s tests

# Single test
python3 -m unittest tests.test_coffee_radar.CoffeeRadarTest.test_parse_feed_and_classify

# HTML report
python3 generate_html.py --input data/items.enriched.jsonl --output reports/report.html
```

## Key conventions

- **Zero dependencies** — pure Python stdlib only. No `pip install`.
- **Chinese output** — traditional characters (zh-TW) throughout.
- **Source kinds**: `feed` (RSS/Atom), `page` (HTML link extraction), `crossref`, `europe_pmc`.
- **Academic filtering** — crossref/europe_pmc sources filtered by `COFFEE_SIGNAL_TERMS` + `UNRELATED_RESEARCH_TERMS`.
- **URL dedup** via `normalize_url()` (scheme+netloc+path, trailing slash stripped).
- **Notion sync dedup** — local SQLite (`data/sync_state.sqlite`) prevents re-importing URLs.
- **Segment reports** — auto-generated in `reports/segments/` unless `--no-segments`.
- **Category keywords** in `CATEGORY_KEYWORDS` dict — modify to adjust classification.
- **Notion API version** pinned to `2022-06-28` in `config.py`.
