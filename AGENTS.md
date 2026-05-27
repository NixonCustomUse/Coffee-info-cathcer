# Coffee Info Catcher — Agent Guide

## Data flow

```
sources.json → coffee_radar.py → data/items.jsonl
                                     ↓
                               coffee_ai.py → data/items.enriched.jsonl
                                                 ↓
                                           coffee_telegram.py → Telegram
                                           coffee_weekly.py   → reports/weekly/
                                           coffee_email.py    → SMTP
                                           generate_html.py   → reports/report.html
```

## Pipeline

```bash
./run_daily_sync.sh
# 1. coffee_radar.py --days 45 --limit 30 --min-score 2  → data/items.jsonl
# 2. coffee_ai.py --input data/items.jsonl               → data/items.enriched.jsonl
# 3. coffee_telegram.py --input data/items.enriched.jsonl --limit 10
```

## Key env vars

| Var | Notes |
|-----|-------|
| `TELEGRAM_BOT_TOKEN` | Required for Telegram |
| `TELEGRAM_CHAT_ID` | Required for Telegram |
| `SMTP_USER` / `SMTP_PASS` / `EMAIL_TO` | Required for email |
| `SMTP_HOST` | Default `smtp.gmail.com` |
| `SMTP_PORT` | Default `587` |
| `EMAIL_FROM` | Defaults to `SMTP_USER` |
| `OPENROUTER_API_KEY` / `OPENAI_API_KEY` | Documented but unused — coffee_ai.py is deterministic only |

## Focused commands

```bash
# Collect only
python3 coffee_radar.py --days 30 --limit 20 --min-score 3

# Enrich only (deterministic fallback, no API calls)
python3 coffee_ai.py --input data/items.jsonl

# Telegram dry run (daily report)
python3 coffee_telegram.py --dry-run

# Telegram dry run (weekly digest)
python3 coffee_telegram.py --digest --dry-run

# Listen for /report and /digest commands
python3 coffee_telegram.py --listen

# Retry until sent (loop every hour)
python3 coffee_telegram.py --loop

# Weekly article
python3 coffee_weekly.py --input data/items.enriched.jsonl

# Email dry run
python3 coffee_email.py --dry-run

# HTML dashboard
python3 generate_html.py --input data/items.enriched.jsonl --output reports/report.html

# Run all tests
python3 -m unittest discover -s tests
python3 -m unittest tests.test_coffee_radar.CoffeeRadarTest.test_parse_feed_and_classify
python3 -m unittest tests.test_sources
```

## Key conventions

- **Zero dependencies** — pure Python stdlib only. No `pip install`.
- **Chinese output** — traditional characters (zh-TW) throughout.
- **Source kinds**: `feed` (RSS/Atom), `page` (HTML link extraction), `reddit` (Atom feed), `crossref`, `europe_pmc`.
- **Academic filtering** — crossref/europe_pmc sources filtered by `COFFEE_SIGNAL_TERMS` + `UNRELATED_RESEARCH_TERMS`.
- **URL dedup** via `normalize_url()` (scheme+netloc+path, trailing slash stripped).
- **Category keywords** in `CATEGORY_KEYWORDS` dict in `coffee/classify.py`.
- **Segment reports** auto-generated in `reports/segments/` (farm, processing, climate-tech, equipment).
- **Item data model** (JSONL): `source`, `title`, `url`, `published`, `summary`, `categories`, `matched_terms`, `score`. After enrichment: `zh_summary`.
- **State tracking**: `data/.telegram_state` prevents duplicate Telegram sends in one day.
- **coffee_radar.py exit codes**: 0 if items collected, 2 if none found.
- **CLI defaults**: most scripts run with sensible defaults — check argparse in each file.

## macOS scheduling

`com.coffee-radar.daily-sync.plist` runs `run_daily_sync.sh` daily at 08:00 via launchd.
Logs to `logs/daily-sync.log` and `logs/daily-sync.err`.
**Contains plaintext Telegram tokens — do not commit.**

## Cloudflare Pages

`wrangler.toml` deploys `public/` as `coffee-info-catcher`. Static frontend ("The Brew") renders embedded signal data.
