# Coffee Info Catcher — Agent Guide

## Data flow

```
sources.json → coffee_radar.py → data/items.jsonl (incl. zh_summary)
                                    ↓
                              reports/latest.md
                              reports/segments/*.md
                              coffee_telegram.py → Telegram
```

## Pipeline

```bash
./run.sh
# or: python3 coffee_radar.py --days 45 --min-score 2
# 1. Collects from all sources → data/items.jsonl
# 2. Enriches with zh_summary (deterministic, no API calls)
# 3. Writes reports/latest.md + reports/segments/*.md
# 4. Sends highlights via Telegram
```

## Key env vars

| Var | Notes |
|-----|-------|
| `OPENROUTER_API_KEY` / `OPENAI_API_KEY` | Not used — enrichment is deterministic only |
| `TELEGRAM_BOT_TOKEN` | Required for Telegram |
| `TELEGRAM_CHAT_ID` | Required for Telegram |

## Focused commands

```bash
# Collect + enrich + reports
python3 coffee_radar.py --days 30 --min-score 3

# Disable enrichment
python3 coffee_radar.py --no-enrich

# Run all tests
python3 -m unittest discover -s tests
```

## Key conventions

- **Zero dependencies** — pure Python stdlib only. No `pip install`.
- **Chinese output** — traditional characters (zh-TW) throughout.
- **Source kinds**: `feed` (RSS/Atom), `page` (HTML link extraction), `reddit` (Atom feed), `crossref`, `europe_pmc`.
- **Academic filtering** — crossref/europe_pmc sources filtered by `COFFEE_SIGNAL_TERMS` + `UNRELATED_RESEARCH_TERMS`.
- **URL dedup** via `normalize_url()` (scheme+netloc+path, trailing slash stripped).
- **Category keywords** in `CATEGORY_KEYWORDS` dict in `coffee/classify.py`.
- **Segment reports** auto-generated in `reports/segments/` (farm, processing, climate-tech, equipment).
- **Item data model** (JSONL): `source`, `title`, `url`, `published`, `summary`, `categories`, `matched_terms`, `score`, `zh_summary`.
- **coffee_radar.py exit codes**: 0 if items collected, 2 if none found.
