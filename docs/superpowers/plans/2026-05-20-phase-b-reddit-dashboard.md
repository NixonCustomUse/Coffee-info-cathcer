# Phase B + D: Reddit Sources & Interactive Dashboard

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Reddit community sources to Coffee Radar, then upgrade the HTML dashboard with interactive filtering.

**Architecture:** Reddit RSS (Atom) feeds are parsed by a new `parse_reddit()` function in `coffee/parsers.py`, routed from `coffee_radar.py:collect()`. The dashboard is a single self-contained HTML file with embedded CSS/JS/JSON.

**Tech Stack:** Python stdlib only (xml.etree.ElementTree, urllib), vanilla JS for frontend.

---

### Task 1: Add `parse_reddit()` to coffee/parsers.py

**Files:**
- Modify: `coffee/parsers.py`
- Test: `tests/test_coffee_radar.py`

- [ ] **Step 1: Read current parsers.py to understand patterns**

Run: `python3 -c "from coffee.parsers import parse_feed, parse_page, parse_crossref, parse_europe_pmc; print('ok')"`
Expected: `ok`

- [ ] **Step 2: Write the failing test**

Add to `tests/test_coffee_radar.py`:

```python
SAMPLE_REDDIT_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/">
  <title>coffee</title>
  <entry>
    <title>Best pourover technique for light roasts?</title>
    <link href="https://www.reddit.com/r/coffee/comments/abc123/" rel="alternate"/>
    <published>2026-05-19T14:30:00+00:00</published>
    <updated>2026-05-19T15:00:00+00:00</updated>
    <author><name>/u/coffeelover</name></author>
    <summary type="html">&lt;p&gt;I've been experimenting with light roasts and found that a slower pour works better.&lt;/p&gt;</summary>
    <media:thumbnail xmlns:media="http://search.yahoo.com/mrss/" url="https://example.com/thumb.jpg"/>
  </entry>
  <entry>
    <title>New espresso machine recommendations under $500</title>
    <link href="https://www.reddit.com/r/espresso/comments/def456/" rel="alternate"/>
    <published>2026-05-18T09:15:00+00:00</published>
    <updated>2026-05-18T10:00:00+00:00</updated>
    <author><name>/u/espresso_fan</name></author>
    <content type="html">&lt;p&gt;Looking for a budget-friendly espresso machine.&lt;/p&gt;</content>
  </entry>
</feed>"""

class CoffeeRadarTest(unittest.TestCase):
    # ... existing methods ...

    def test_reddit_parser(self):
        source = Source(name="r/coffee", url="https://www.reddit.com/r/coffee/.rss", kind="reddit")
        items = parse_reddit(source, SAMPLE_REDDIT_RSS)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].title, "Best pourover technique for light roasts?")
        self.assertIn("coffee", items[0].url)
        self.assertEqual(items[0].published, "2026-05-19T14:30:00+00:00")
        self.assertEqual(items[1].title, "New espresso machine recommendations under $500")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m unittest tests.test_coffee_radar.CoffeeRadarTest.test_reddit_parser -v`
Expected: `FAIL` with `NameError: name 'parse_reddit' is not defined`

- [ ] **Step 4: Write minimal parse_reddit() implementation**

Add to `coffee/parsers.py`:

```python
def parse_reddit(source: Source, raw: str) -> list[Item]:
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(raw)
    items: list[Item] = []
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        link_el = entry.find("atom:link[@rel='alternate']", ns)
        pub_el = entry.find("atom:published", ns)
        content_el = entry.find("atom:content", ns)
        summary_el = entry.find("atom:summary", ns)

        title = clean_text(title_el.text) if title_el is not None and title_el.text else ""
        url = link_el.get("href", "") if link_el is not None else ""
        published = pub_el.text.strip() if pub_el is not None and pub_el.text else ""

        raw_text = ""
        if content_el is not None and content_el.text:
            raw_text = clean_text(content_el.text)
        elif summary_el is not None and summary_el.text:
            raw_text = clean_text(summary_el.text)

        item = Item(source=source.name, title=title, url=normalize_url(url), published=published, summary=raw_text)
        items.append(item)
    return items
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m unittest tests.test_coffee_radar.CoffeeRadarTest.test_reddit_parser -v`
Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add coffee/parsers.py tests/test_coffee_radar.py
git commit -m "feat: add parse_reddit() for Reddit RSS feeds"
```

---

### Task 2: Wire reddit kind into collector + add sources

**Files:**
- Modify: `sources.json`
- Modify: `coffee_radar.py`
- Modify: `coffee/__init__.py`

- [ ] **Step 1: Add parse_reddit to coffee/__init__.py re-exports**

Edit `coffee/__init__.py`, add `parse_reddit` to the import from `coffee.parsers`:

```python
from coffee.parsers import (
    parse_feed, parse_page, parse_crossref, parse_europe_pmc, parse_reddit,
)
```

- [ ] **Step 2: Add reddit routing in coffee_radar.py**

Read `coffee_radar.py`, find the `collect()` function where kind dispatch happens. Add `"reddit"` entry:

```python
PARSER_FOR_KIND = {
    "feed": parse_feed,
    "page": parse_page,
    "crossref": parse_crossref,
    "europe_pmc": parse_europe_pmc,
    "reddit": parse_reddit,
}
```

- [ ] **Step 3: Add 6 Reddit sources to sources.json**

Append after the last entry in `sources.json`:

```json
  },
  {
    "name": "r/coffee",
    "url": "https://www.reddit.com/r/coffee/.rss",
    "kind": "reddit",
    "enabled": true
  },
  {
    "name": "r/espresso",
    "url": "https://www.reddit.com/r/espresso/.rss",
    "kind": "reddit",
    "enabled": true
  },
  {
    "name": "r/roasting",
    "url": "https://www.reddit.com/r/roasting/.rss",
    "kind": "reddit",
    "enabled": true
  },
  {
    "name": "r/pourover",
    "url": "https://www.reddit.com/r/pourover/.rss",
    "kind": "reddit",
    "enabled": true
  },
  {
    "name": "r/cafe",
    "url": "https://www.reddit.com/r/cafe/.rss",
    "kind": "reddit",
    "enabled": true
  },
  {
    "name": "r/coffeesnobs",
    "url": "https://www.reddit.com/r/coffeesnobs/.rss",
    "kind": "reddit",
    "enabled": true
  }
```

- [ ] **Step 4: Run existing tests to confirm nothing broke**

Run: `python3 -m unittest discover -s tests -v`
Expected: all 13 tests pass

- [ ] **Step 5: Do a quick collection test**

Run: `python3 coffee_radar.py --days 1 --limit 5 --min-score 0 --silent 2>&1 | head -20`
Expected: collects data, mentions reddit sources in progress

- [ ] **Step 6: Commit**

```bash
git add coffee/__init__.py coffee_radar.py sources.json
git commit -m "feat: wire reddit kind into collector, add 6 subreddit sources"
```

---

### Task 3: Rewrite generate_html.py with interactive filters

**Files:**
- Overwrite: `generate_html.py`
- Test: manual verification with browser

- [ ] **Step 1: Verify current generate_html.py output format**

Run: `python3 generate_html.py --input data/items.enriched.jsonl --output /tmp/old-report.html`
Expected: report saved

- [ ] **Step 2: Write the new generate_html.py**

Replace the entire file. The script reads JSONL, embeds JSON data in the HTML, and generates a single self-contained page with:

- Category dropdown filter (multi-select via checkboxes in a dropdown)
- Source dropdown filter (same pattern)
- Date range inputs (start/end)
- Search text input
- Sort selector (score desc / date desc)
- Filtered card grid

Key implementation details:
- JSON data embedded in `<script id="app-data" type="application/json">` 
- All filtering happens client-side in vanilla JS
- CSS in `<style>`, JS in `<script>`
- Each card shows: score badge, title (linked), source, categories (colored tags), zh_summary or summary, matched_terms

```python
#!/usr/bin/env python3
"""Generate an interactive HTML dashboard from JSONL data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from coffee.util import load_jsonl


def build_html(items: list[dict]) -> str:
    # Extract unique categories and sources for filter options
    all_cats = sorted({c for i in items for c in i.get("categories", [])})
    all_sources = sorted({i.get("source", "") for i in items})

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Coffee Radar Dashboard</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f5f5f0; color: #2c2c2c; padding: 24px; line-height: 1.5;
  }}
  .container {{ max-width: 1000px; margin: 0 auto; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 4px; }}
  .subtitle {{ color: #888; font-size: 0.85rem; margin-bottom: 20px; }}
  .filters {{
    display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px;
    align-items: center;
  }}
  .filters input, .filters select {{
    padding: 6px 10px; border: 1px solid #d0d0c8; border-radius: 6px;
    font-size: 0.82rem; background: #fff;
  }}
  .filters input[type="text"] {{ min-width: 160px; }}
  .filters label {{ font-size: 0.78rem; color: #888; }}
  .filter-group {{
    display: flex; align-items: center; gap: 4px;
    background: #fff; padding: 4px 8px; border-radius: 6px;
    border: 1px solid #d0d0c8;
  }}
  .filter-group select {{ border: none; padding: 4px; font-size: 0.82rem; outline: none; }}
  .stats {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }}
  .stat-box {{
    background: #fff; padding: 10px 16px; border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }}
  .stat-box .num {{ font-size: 1.2rem; font-weight: 700; }}
  .stat-box .label {{ font-size: 0.7rem; color: #888; text-transform: uppercase; }}
  #result-count {{ font-size: 0.82rem; color: #888; margin-bottom: 12px; }}
  .card {{
    background: #fff; border-radius: 10px; padding: 16px 18px;
    margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }}
  .card-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }}
  .score {{
    background: #1a1a1a; color: #fff; font-size: 0.65rem; font-weight: 700;
    width: 22px; height: 22px; border-radius: 5px; display: inline-flex;
    align-items: center; justify-content: center; flex-shrink: 0;
  }}
  .title {{ font-weight: 600; color: #1a1a1a; text-decoration: none; font-size: 0.93rem; }}
  .title:hover {{ text-decoration: underline; }}
  .meta {{ font-size: 0.78rem; color: #999; margin-bottom: 6px; }}
  .tags {{ display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 6px; }}
  .tag {{
    background: #f0efe8; padding: 2px 10px; border-radius: 12px;
    font-size: 0.72rem; color: #666;
  }}
  .summary {{ font-size: 0.85rem; color: #444; margin-bottom: 4px; }}
  .terms {{ display: flex; gap: 4px; flex-wrap: wrap; }}
  .term {{
    background: #f5f5f0; border: 1px solid #e0e0d8; padding: 1px 7px;
    border-radius: 4px; font-size: 0.68rem; color: #999;
  }}
  .hidden {{ display: none !important; }}
  @media (max-width: 600px) {{
    body {{ padding: 12px; }}
    .filters input[type="text"] {{ min-width: 120px; }}
  }}
</style>
</head>
<body>
<div class="container">
  <h1>Coffee Radar</h1>
  <div class="subtitle">{len(items)} 筆資料 · {len(all_cats)} 分類 · {len(all_sources)} 來源</div>

  <div class="filters">
    <input type="text" id="search" placeholder="搜尋標題或摘要..." oninput="render()">
    <div class="filter-group">
      <label>分類</label>
      <select id="cat-filter" multiple onchange="render()">
        {"".join(f'<option value="{c}">{c}</option>' for c in all_cats)}
      </select>
    </div>
    <div class="filter-group">
      <label>來源</label>
      <select id="src-filter" multiple onchange="render()">
        {"".join(f'<option value="{s}">{s}</option>' for s in all_sources)}
      </select>
    </div>
    <div class="filter-group">
      <label>排序</label>
      <select id="sort" onchange="render()">
        <option value="score-desc">分數 ↓</option>
        <option value="date-desc">日期 ↓</option>
      </select>
    </div>
  </div>

  <div class="stats" id="stats"></div>
  <div id="result-count"></div>
  <div id="cards"></div>
</div>

<script id="app-data" type="application/json">{json.dumps(items, ensure_ascii=False)}</script>
<script>
const DATA = JSON.parse(document.getElementById('app-data').textContent);

function getFilterValues(selId) {{
  const sel = document.getElementById(selId);
  return Array.from(sel.selectedOptions).map(o => o.value);
}}

function render() {{
  const query = document.getElementById('search').value.toLowerCase();
  const cats = getFilterValues('cat-filter');
  const srcs = getFilterValues('src-filter');
  const sort = document.getElementById('sort').value;

  let filtered = DATA.filter(item => {{
    if (query && !item.title.toLowerCase().includes(query) && !(item.zh_summary || item.summary || '').toLowerCase().includes(query)) return false;
    if (cats.length && !item.categories.some(c => cats.includes(c))) return false;
    if (srcs.length && !srcs.includes(item.source)) return false;
    return true;
  }});

  if (sort === 'score-desc') filtered.sort((a, b) => (b.score || 0) - (a.score || 0));
  else if (sort === 'date-desc') filtered.sort((a, b) => (b.published || '').localeCompare(a.published || ''));

  document.getElementById('result-count').textContent = `顯示 ${filtered.length} / ${DATA.length} 筆`;

  const totalScore = filtered.reduce((s, i) => s + (i.score || 0), 0);
  const uniqueSrcs = new Set(filtered.map(i => i.source)).size;
  document.getElementById('stats').innerHTML = `
    <div class="stat-box"><div class="num">${{filtered.length}}</div><div class="label">篩選後</div></div>
    <div class="stat-box"><div class="num">${{uniqueSrcs}}</div><div class="label">來源</div></div>
    <div class="stat-box"><div class="num">${{totalScore}}</div><div class="label">總分</div></div>
  `;

  document.getElementById('cards').innerHTML = filtered.map(item => {{
    const catsHtml = (item.categories || []).map(c => `<span class="tag">${{c}}</span>`).join('');
    const termsHtml = (item.matched_terms || []).slice(0, 6).map(t => `<span class="term">${{t}}</span>`).join('');
    const summary = item.zh_summary || item.summary || '';
    return `<div class="card">
      <div class="card-header">
        <span class="score">${{item.score || 0}}</span>
        <a href="${{item.url}}" target="_blank" class="title">${{item.title}}</a>
      </div>
      <div class="meta">${{item.source}} · ${{(item.published || '').slice(0, 10)}}</div>
      <div class="tags">${{catsHtml}}</div>
      <div class="summary">${{summary}}</div>
      <div class="terms">${{termsHtml}}</div>
    </div>`;
  }}).join('');
}}

render();
</script>
</body>
</html>"""


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate interactive HTML dashboard from JSONL.")
    parser.add_argument("--input", default="data/items.enriched.jsonl")
    parser.add_argument("--output", default="reports/report.html")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    items = load_jsonl(Path(args.input))
    if not items:
        print("No items found.")
        return 1
    html = build_html(items)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Saved dashboard: {out.resolve()} ({len(html)} bytes, {len(items)} items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Generate and verify the dashboard**

Run: `python3 generate_html.py --input data/items.enriched.jsonl --output /tmp/dashboard.html && open /tmp/dashboard.html`
Expected: browser opens with interactive dashboard, filtering works

- [ ] **Step 4: Run full pipeline test**

Run: `python3 -m unittest discover -s tests -v`
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add generate_html.py
git commit -m "feat: interactive HTML dashboard with category/source/search filters"
```
