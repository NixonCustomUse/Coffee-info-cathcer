# Simplify Coffee Info Catcher Pipeline

## Motivation

The project has accumulated many output channels (Telegram, email, weekly, HTML, Cloudflare)
that are no longer used. We also have a 3-step pipeline that can be consolidated into a
single CLI, reducing cognitive overhead and maintenance surface.

## What Changes

### Removed files (delete entirely)

- `coffee_telegram.py` — Telegram notification (336 lines)
- `coffee_weekly.py` — Weekly article generation (148 lines)
- `coffee_email.py` — SMTP email sending (110 lines)
- `generate_html.py` — HTML dashboard (286 lines)
- `index.html` — Frontend (root copy)
- `public/` — Cloudflare Pages deployment directory
- `wrangler.toml` — Cloudflare configuration
- `com.coffee-radar.daily-sync.plist` — macOS launchd scheduler (contains secrets)
- `run_daily_sync.sh` — Replaced by `run.sh`
- `run_coffee_radar.sh` — Replaced by `run.sh`

### Merged logic

`coffee_ai.py` enrichment logic moves into `coffee_radar.py` as an `--enrich` flag
(default: on). The deterministic `fallback_summary_zh()` becomes an internal function
in `coffee_radar.py`.

### Modified files

**`coffee_radar.py`:**
- Add `--enrich` / `--no-enrich` flag (default: enrich)
- Add `--jsonl` flag already exists, output always includes `zh_summary` when enriched
- Inline `fallback_summary_zh()` and `summarize_item_zh()` from `coffee_ai.py`
- Keep `--limit` flag (only affects markdown reports; JSONL always full — no behavioral change)
- Import `strip_feed_boilerplate` and `clean_text` from `coffee.util` (already used)

**`coffee/__init__.py`:**
- No changes needed (already exports everything `coffee_radar.py` needs)
- (Optional) Remove `load_jsonl`, `write_jsonl` re-exports if unused elsewhere

**`run.sh`** (new, replaces both `run_daily_sync.sh` and `run_coffee_radar.sh`):
```bash
#!/bin/bash
python3 coffee_radar.py --days 45 --min-score 2
```

### Files that stay unchanged

- `coffee/util.py` — utility functions
- `coffee/sources.py` — Source dataclass + loader
- `coffee/classify.py` — Item dataclass, classification, filtering, dedup
- `coffee/parsers.py` — Feed/page/Reddit/academic parsers
- `coffee/report.py` — Markdown + segment report writers
- `config.py` — central config (currently empty beyond NOTION_VERSION)
- `sources.json` — source configuration
- `tests/test_coffee_radar.py` — update to test enrichment
- `tests/test_sources.py` — unchanged
- `data/`, `reports/`, `logs/` — output directories (unchanged structure)

### Updated `AGENTS.md`

Replace pipeline section to show single-step command, remove Telegram/email/weekly/HTML
references.

## Data flow (after)

```
sources.json → coffee_radar.py (--enrich) → data/items.jsonl (incl. zh_summary)
                                             → reports/latest.md
                                             → reports/segments/*.md
```

## Not changing

- Zero-dependency constraint (pure stdlib)
- Chinese (zh-TW) output convention
- All 5 source kinds (feed, page, crossref, europe_pmc, reddit)
- Score/category/segment logic
- File output locations
- Test framework (unittest)

## Edge cases

- `coffee_ai.py` is imported by no other script, so removal is safe
- Running `coffee_radar.py` without `--enrich` produces JSONL without `zh_summary`
  (backward-compatible with existing consumers, though after cleanup there are none)
- The `reports/` directory still writes markdown and segment reports
