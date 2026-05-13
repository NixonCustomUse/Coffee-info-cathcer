# Coffee Info Catcher Restructure Design

> **Goal:** Restructure flat Python modules into a focused `coffee/` package, remove LLM/AI integration, and sharpen AGENTS.md.

**Architecture:** Extract 5 single-responsibility submodules from the 842-line `coffee_radar.py`, move weekly article functions into `coffee_weekly.py`, and delete all OpenRouter/LLM API calls. Pipeline interface and data format stay unchanged.

**Tech Stack:** Python 3 stdlib only (unchanged). No new dependencies.

---

## 1. Package structure

```
coffee/                  # NEW — single-responsibility submodules
  __init__.py            # Re-export everything consumers need
  sources.py             # Source dataclass + load_sources()
  parsers.py             # parse_feed / parse_page / parse_crossref / parse_europe_pmc + LinkExtractor
  classify.py            # Item dataclass, CATEGORY_KEYWORDS, classify(), is_relevant_item(), dedupe(), SEGMENT_DEFINITIONS
  report.py              # write_markdown(), write_segment_reports(), write_segment_report(), progress_line()
  util.py                # clean_text(), normalize_url(), parse_date(), fetch_text(), fetch_json(), UTC, write_jsonl()

coffee_radar.py          # EDIT — slimmed to collect() + main() + CLI, imports from coffee/
coffee_ai.py             # EDIT — LLM calls removed, always fallback
coffee_weekly.py         # EDIT — gains generate_weekly_article() family
coffee_notion_sync.py    # EDIT — import paths updated
generate_html.py         # EDIT — import paths updated, deduplicate load_jsonl()
config.py                # NO CHANGE — LLM vars remain but unused
AGENTS.md                # EDIT — shortened to agent-specific guidance
tests/test_coffee_radar.py  # EDIT — import paths updated, unneeded tests removed
```

Every external module (`coffee_radar.py`, `coffee_ai.py`, `coffee_notion_sync.py`, `coffee_weekly.py`, `generate_html.py`, tests) changes only three things:
1. `from coffee_radar import X` → `from coffee.xxx import X`
2. (for coffee_ai) remove LLM code
3. (for coffee_weekly) gain functions that were in coffee_ai

## 2. coffee/ submodule boundaries

### `coffee/sources.py`
- `Source` dataclass (name, url, kind, enabled, tags)
- `load_sources()` — reads `sources.json`, filters by `enabled`
- `USER_AGENT` constant

### `coffee/parsers.py`
- All four parsers: `parse_feed()`, `parse_page()`, `parse_crossref()`, `parse_europe_pmc()`
- `LinkExtractor` (HTMLParser subclass)
- Helper functions: `first_text()`, `first_link()`, `local_name()`, `wanted_names()`, `normalize_xml_entities()`, `date_parts_to_rfc3339()`

### `coffee/classify.py`
- `Item` dataclass
- `CATEGORY_KEYWORDS` dict, `COFFEE_SIGNAL_TERMS`, `UNRELATED_RESEARCH_TERMS`
- `SEGMENT_DEFINITIONS` dict
- `classify()`, `keyword_in_text()`, `is_relevant_item()`, `is_recent()`, `dedupe()`, `sort_key()`, `item_matches_segment()`
- `item_to_dict()` — converts Item → dict for JSON serialization

### `coffee/report.py`
- `write_markdown()` — full report
- `write_segment_report()`, `write_segment_reports()` — per-segment reports
- `progress_line()`, `truncate_label()` — terminal progress display

### `coffee/util.py`
- `clean_text()`, `normalize_url()`, `parse_date()`
- `fetch_text()`, `fetch_json()`
- `UTC`, `write_jsonl()`, `load_jsonl()`

## 3. AI removal — coffee_ai.py

**Deleted:**
- `openai_text()` — entire OpenRouter/LLM request function
- `extract_response_text()`
- `build_weekly_prompt()` — only used by AI weekly

**Simplified:**
- `summarize_item_zh()` — always calls `fallback_summary_zh()`, remove `use_ai` param
- `generate_weekly_article()` — always calls `fallback_weekly_article()`, remove `use_ai` param
- `enrich_items()` — remove `use_ai`, `force` params
- `main()` — remove "LLM_API_KEY missing" warning

**Moved to coffee_weekly.py:**
- `generate_weekly_article()`, `fallback_weekly_article()`, `pick_items()`, `format_category_counts()`, `render_item_paragraph()`, `week_title()`, `output_paths()`, `select_recent_items()`, `item_date()`

**Stays in coffee_ai.py:**
- `fallback_summary_zh()`, `strip_feed_boilerplate()`, `compact_signal_zh()`
- `summarize_item_zh()` (now always fallback)

To avoid circular imports: `compact_signal_zh()` is used by both `fallback_summary_zh()` (coffee_ai) and `fallback_weekly_article()` (coffee_weekly). Move `compact_signal_zh()` to `coffee/util.py`.

## 4. coffee_weekly.py changes

After gaining functions from coffee_ai.py:
- Drop `import config`
- `main()` — remove "LLM_API_KEY missing" warning

## 5. generate_html.py changes

- Replace its own `load_jsonl()` with `from coffee.util import load_jsonl`

## 6. config.py

- No changes. LLM vars remain but become unused.

## 7. Tests

`tests/test_coffee_radar.py`:
- Update all imports: `from coffee_radar import X` → `from coffee.classify import X`, `from coffee.parsers import X`, `from coffee.sources import X`
- Import coffee_ai functions from `coffee_ai` directly (not changed)
- Import coffee_weekly functions from `coffee_weekly`

Test layout after:
- `tests/test_coffee_radar.py` — core radar tests (feed, crossref, europe_pmc, classification, segment, dedup)
- `tests/test_coffee_ai.py` — summary tests (fallback_summary_zh, compact_signal_zh)
- `tests/test_coffee_weekly.py` — weekly article tests (generate_weekly_article, select_recent_items)
- `tests/test_coffee_notion_sync.py` — sync state tests (add if needed)

## 8. AGENTS.md

Trim from 72 lines to ~40 lines. Keep: data-flow diagram, pipeline run order, env vars table, focused CLI commands, key conventions (URL dedup, category keywords, academic filters). Remove project structure tree and content duplicated with README.

## 9. Implementation order

1. Create `coffee/util.py`
2. Create `coffee/sources.py`
3. Create `coffee/parsers.py`
4. Create `coffee/classify.py`
5. Create `coffee/report.py`
6. Create `coffee/__init__.py`
7. Slim `coffee_radar.py`
8. Edit `coffee_ai.py` — remove LLM, move weekly functions out
9. Edit `coffee_weekly.py`
10. Edit `coffee_notion_sync.py`
11. Edit `generate_html.py`
12. Edit `AGENTS.md`
13. Edit `tests/test_coffee_radar.py`
14. Run full test suite: `python3 -m unittest discover -s tests`
