# Simplify Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove unused output channels, merge enrichment into the collector, and produce a single-step pipeline.

**Architecture:** All enrichment logic from `coffee_ai.py` moves inline into `coffee_radar.py` behind an `--enrich` flag. Ten unused files are deleted. A single `run.sh` replaces two previous shell scripts.

**Tech Stack:** Pure Python 3 stdlib, no dependencies.

---

### Task 1: Delete unused output channel files

**Files:**
- Delete: `coffee_telegram.py`
- Delete: `coffee_weekly.py`
- Delete: `coffee_email.py`
- Delete: `generate_html.py`
- Delete: `index.html`
- Delete: `public/index.html`
- Delete: `wrangler.toml`
- Delete: `com.coffee-radar.daily-sync.plist`
- Delete: `run_daily_sync.sh`
- Delete: `run_coffee_radar.sh`

- [ ] **Step 1: Delete 10 files**

```bash
git rm coffee_telegram.py coffee_weekly.py coffee_email.py generate_html.py
git rm index.html public/index.html wrangler.toml com.coffee-radar.daily-sync.plist
git rm run_daily_sync.sh run_coffee_radar.sh
git rm -r public/  
# If public/ only contained index.html, rmdir it too
```

- [ ] **Step 2: Commit**

```bash
git commit -m "chore: remove unused output channels (telegram, email, weekly, html, cloudflare)"
```

---

### Task 2: Merge enrichment logic into coffee_radar.py

**Files:**
- Modify: `coffee_radar.py`
- Delete: `coffee_ai.py`

- [ ] **Step 1: Add `--enrich`/`--no-enrich` flag to the argument parser**

Add to `build_arg_parser()` in `coffee_radar.py`:

```python
    parser.add_argument(
        "--enrich", action=argparse.BooleanOptionalAction, default=True,
        help="Add zh_summary to JSONL output (default: on).",
    )
```

- [ ] **Step 2: Add enrichment functions internally**

Add to `coffee_radar.py` (before `build_arg_parser`, after imports):

```python
import textwrap

from coffee.util import clean_text, strip_feed_boilerplate


def _fallback_summary_zh(item: dict[str, object]) -> str:
    title = clean_text(str(item.get("title", "")))
    source = item.get("source", "未知來源")
    categories = "、".join(item.get("categories", ["其他咖啡動態"]))
    summary = clean_text(str(item.get("summary", "")))
    if summary:
        summary = strip_feed_boilerplate(summary)
        summary = textwrap.shorten(summary, width=190, placeholder="...")
        return f"這篇來自 {source}，主題是「{title}」。目前歸類為{categories}。來源摘要重點：{summary}"
    return f"這篇來自 {source}，主題是「{title}」。目前歸類為{categories}，值得後續追蹤原文細節。"


def _summarize_item_zh(item: dict[str, object]) -> str:
    return _fallback_summary_zh(item)


def _enrich_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    enriched: list[dict[str, object]] = []
    for item in items:
        next_item = dict(item)
        if not next_item.get("zh_summary"):
            next_item["zh_summary"] = _summarize_item_zh(next_item)
        enriched.append(next_item)
    return enriched
```

- [ ] **Step 3: Wire enrichment into `main()`**

Change the main function to enrich before writing:

```python
def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    source_path = Path(args.sources)
    sources = load_sources(source_path)
    items, errors = collect(sources, days=args.days, minimum_score=args.min_score)
    jsonl_items = [item_to_dict(i) for i in items]
    if args.enrich:
        jsonl_items = _enrich_items(jsonl_items)
    write_markdown(items, errors, Path(args.out), limit=args.limit)
    write_jsonl(jsonl_items, Path(args.jsonl))
    if not args.no_segments:
        write_segment_reports(items, Path(args.segment_dir), limit=args.limit)
    ...
```

- [ ] **Step 4: Delete `coffee_ai.py`**

```bash
git rm coffee_ai.py
```

- [ ] **Step 5: Verify the script runs**

```bash
python3 coffee_radar.py --days 90 --min-score 1 --no-enrich --limit 3
# Should produce data/items.jsonl WITHOUT zh_summary
python3 -c "import json; d=json.loads(open('data/items.jsonl').readline()); print('zh_summary' in d)"
# Expected output: False
```

```bash
python3 coffee_radar.py --days 90 --min-score 1 --enrich --limit 3
# Should produce data/items.jsonl WITH zh_summary
python3 -c "import json; d=json.loads(open('data/items.jsonl').readline()); print('zh_summary' in d)"
# Expected output: True
```

- [ ] **Step 6: Commit**

```bash
git add coffee_radar.py
git commit -m "refactor: merge coffee_ai.py enrichment into coffee_radar.py --enrich flag"
```

---

### Task 3: Create run.sh

**Files:**
- Create: `run.sh`

- [ ] **Step 1: Write run.sh**

```bash
#!/bin/bash
set -euo pipefail
python3 coffee_radar.py --days 45 --min-score 2
```

- [ ] **Step 2: Make executable**

```bash
chmod +x run.sh
```

- [ ] **Step 3: Commit**

```bash
git add run.sh
git commit -m "feat: add run.sh (single-step pipeline)"
```

---

### Task 4: Update AGENTS.md

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: Update pipeline section**

Replace the old 3-step pipeline with:

```
## Pipeline

```bash
./run.sh
# or: python3 coffee_radar.py --days 45 --min-score 2
# 1. Collects from all sources → data/items.jsonl
# 2. Enriches with zh_summary (deterministic, no API calls)
# 3. Writes reports/latest.md + reports/segments/*.md
```

- [ ] **Step 2: Remove references to deleted scripts**

Remove the `coffee_telegram.py`, `coffee_weekly.py`, `coffee_email.py`, `generate_html.py` entries from the "Focused commands" table and the data flow diagram.

- [ ] **Step 3: Commit**

```bash
git add AGENTS.md
git commit -m "docs: update AGENTS.md for simplified pipeline"
```

---

### Task 5: Update tests

**Files:**
- Modify: `tests/test_coffee_radar.py`

- [ ] **Step 1: Check existing tests for references to deleted files**

Run a grep to find anything referencing removed scripts:

```bash
rg -l "telegram|weekly|email|generate_html|coffee_ai" tests/
```

- [ ] **Step 2: Add enrichment test**

Add to `tests/test_coffee_radar.py`:

```python
def test_enrich_items_adds_zh_summary(self):
    from coffee_radar import _enrich_items
    items = [{"title": "New Coffee Sensor", "source": "Test", "categories": ["設備/自動化"], "summary": "A new sensor for coffee roasting."}]
    enriched = _enrich_items(items)
    self.assertIn("zh_summary", enriched[0])
    self.assertIn("設備/自動化", enriched[0]["zh_summary"])
```

- [ ] **Step 3: Run tests**

```bash
python3 -m unittest discover -s tests -v
```

Expected: all existing tests pass, new test passes.

- [ ] **Step 4: Commit**

```bash
git add tests/test_coffee_radar.py
git commit -m "test: add enrichment test for coffee_radar.py"
```

---

### Task 6: Final cleanup verification

- [ ] **Step 1: Verify no dangling imports/references**

```bash
rg -l "coffee_telegram|coffee_weekly|coffee_email|generate_html" --type py
# Expected: no output
```

```bash
rg "from coffee_ai|import coffee_ai" --type py
# Expected: no output
```

- [ ] **Step 2: Run full test suite**

```bash
python3 -m unittest discover -s tests -v
```
