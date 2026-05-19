#!/usr/bin/env python3
"""Generate an interactive HTML dashboard from JSONL data."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from coffee.util import load_jsonl


def build_html(items: list[dict]) -> str:
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
        {"".join(f'<option value="{html.escape(c)}">{html.escape(c)}</option>' for c in all_cats)}
      </select>
    </div>
    <div class="filter-group">
      <label>來源</label>
      <select id="src-filter" multiple onchange="render()">
        {"".join(f'<option value="{html.escape(s)}">{html.escape(s)}</option>' for s in all_sources)}
      </select>
    </div>
    <div class="filter-group">
      <label>排序</label>
      <select id="sort" onchange="render()">
        <option value="score-desc">分數 ↓</option>
        <option value="date-desc">日期 ↓</option>
      </select>
    </div>
    <div class="filter-group">
      <label>從</label>
      <input type="date" id="date-from" onchange="render()">
    </div>
    <div class="filter-group">
      <label>到</label>
      <input type="date" id="date-to" onchange="render()">
    </div>
  </div>

  <div class="stats" id="stats"></div>
  <div id="result-count"></div>
  <div id="cards"></div>
</div>

<script id="app-data" type="application/json">{json.dumps(items, ensure_ascii=False)}</script>
<script>
function esc(str) {{
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}}
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
    const dateFrom = document.getElementById('date-from').value;
    const dateTo = document.getElementById('date-to').value;
    if (dateFrom && (item.published || '').slice(0, 10) < dateFrom) return false;
    if (dateTo && (item.published || '').slice(0, 10) > dateTo) return false;
    return true;
  }});

  if (sort === 'score-desc') filtered.sort((a, b) => (b.score || 0) - (a.score || 0));
  else if (sort === 'date-desc') filtered.sort((a, b) => (b.published || '').localeCompare(a.published || ''));

  document.getElementById('result-count').textContent = `顯示 ${{filtered.length}} / ${{DATA.length}} 筆`;

  const totalScore = filtered.reduce((s, i) => s + (i.score || 0), 0);
  const uniqueSrcs = new Set(filtered.map(i => i.source)).size;
  document.getElementById('stats').innerHTML = `
    <div class="stat-box"><div class="num">${{esc(filtered.length)}}</div><div class="label">篩選後</div></div>
    <div class="stat-box"><div class="num">${{esc(uniqueSrcs)}}</div><div class="label">來源</div></div>
    <div class="stat-box"><div class="num">${{esc(totalScore)}}</div><div class="label">總分</div></div>
  `;

  document.getElementById('cards').innerHTML = filtered.map(item => {{
    const catsHtml = (item.categories || []).map(c => `<span class="tag">${{esc(c)}}</span>`).join('');
    const termsHtml = (item.matched_terms || []).slice(0, 6).map(t => `<span class="term">${{esc(t)}}</span>`).join('');
    const summary = item.zh_summary || item.summary || '';
    return `<div class="card">
      <div class="card-header">
        <span class="score">${{item.score || 0}}</span>
        <a href="${{item.url}}" target="_blank" class="title">${{esc(item.title)}}</a>
      </div>
      <div class="meta">${{esc(item.source)}} · ${{esc((item.published || '').slice(0, 10))}}</div>
      <div class="tags">${{catsHtml}}</div>
      <div class="summary">${{esc(summary)}}</div>
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
