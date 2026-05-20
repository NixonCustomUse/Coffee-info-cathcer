#!/usr/bin/env python3
"""Generate an interactive HTML dashboard from JSONL data."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from coffee.util import load_jsonl


CSS = """\
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f5f5f0; color: #2c2c2c; padding: 24px; line-height: 1.5;
  }
  .container { max-width: 1000px; margin: 0 auto; }
  h1 { font-size: 1.4rem; margin-bottom: 4px; }
  .subtitle { color: #888; font-size: 0.85rem; margin-bottom: 20px; }
  .filters {
    display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px;
    align-items: center;
  }
  .filters input, .filters select {
    padding: 6px 10px; border: 1px solid #d0d0c8; border-radius: 6px;
    font-size: 0.82rem; background: #fff;
  }
  .filters input[type="text"] { min-width: 160px; }
  .filters label { font-size: 0.78rem; color: #888; }
  .filter-group {
    display: flex; align-items: center; gap: 4px;
    background: #fff; padding: 4px 8px; border-radius: 6px;
    border: 1px solid #d0d0c8;
  }
  .filter-group select { border: none; padding: 4px; font-size: 0.82rem; outline: none; }
  .stats { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
  .stat-box {
    background: #fff; padding: 10px 16px; border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }
  .stat-box .num { font-size: 1.2rem; font-weight: 700; }
  .stat-box .label { font-size: 0.7rem; color: #888; text-transform: uppercase; }
  #result-count { font-size: 0.82rem; color: #888; margin-bottom: 12px; }
  .card {
    background: #fff; border-radius: 10px; padding: 16px 18px;
    margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }
  .card-header { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
  .score {
    background: #1a1a1a; color: #fff; font-size: 0.65rem; font-weight: 700;
    width: 22px; height: 22px; border-radius: 5px; display: inline-flex;
    align-items: center; justify-content: center; flex-shrink: 0;
  }
  .title { font-weight: 600; color: #1a1a1a; text-decoration: none; font-size: 0.93rem; }
  .title:hover { text-decoration: underline; }
  .meta { font-size: 0.78rem; color: #999; margin-bottom: 6px; }
  .tags { display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 6px; }
  .tag {
    background: #f0efe8; padding: 2px 10px; border-radius: 12px;
    font-size: 0.72rem; color: #666;
  }
  .summary { font-size: 0.85rem; color: #444; margin-bottom: 4px; }
  .terms { display: flex; gap: 4px; flex-wrap: wrap; }
  .term {
    background: #f5f5f0; border: 1px solid #e0e0d8; padding: 1px 7px;
    border-radius: 4px; font-size: 0.68rem; color: #999;
  }
  .hidden { display: none !important; }
  .date-heading {
    font-size: 0.95rem; font-weight: 600; color: #555;
    margin: 20px 0 8px; padding-bottom: 4px;
    border-bottom: 1px solid #e0e0d8;
  }
  .toggle-group {
    display: flex; align-items: center; gap: 6px;
    font-size: 0.82rem; color: #666;
  }
  .toggle-group input { width: 16px; height: 16px; cursor: pointer; }
  @media (max-width: 600px) {
    body { padding: 12px; }
    .filters input[type="text"] { min-width: 120px; }
  }
"""

JS_SCRIPT = """
function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}
const DATA = JSON.parse(document.getElementById('app-data').textContent);

function getFilterValues(selId) {
  const sel = document.getElementById(selId);
  return Array.from(sel.selectedOptions).map(function(o) { return o.value; });
}

function cardHtml(item) {
  var catsHtml = (item.categories || []).map(function(c) { return '<span class="tag">' + esc(c) + '</span>'; }).join('');
  var termsHtml = (item.matched_terms || []).slice(0, 6).map(function(t) { return '<span class="term">' + esc(t) + '</span>'; }).join('');
  var summary = item.zh_summary || item.summary || '';
  return '<div class="card">'
    + '<div class="card-header">'
    + '<span class="score">' + (item.score || 0) + '</span>'
    + '<a href="' + item.url + '" target="_blank" class="title">' + esc(item.title) + '</a></div>'
    + '<div class="meta">' + esc(item.source) + ' &middot; ' + esc((item.published || '').slice(0, 10)) + '</div>'
    + '<div class="tags">' + catsHtml + '</div>'
    + '<div class="summary">' + esc(summary) + '</div>'
    + '<div class="terms">' + termsHtml + '</div>'
    + '</div>';
}

function render() {
  var query = document.getElementById('search').value.toLowerCase();
  var cats = getFilterValues('cat-filter');
  var srcs = getFilterValues('src-filter');
  var sort = document.getElementById('sort').value;
  var group = document.getElementById('group-view').checked;

  var filtered = DATA.filter(function(item) {
    if (query && item.title.toLowerCase().indexOf(query) === -1 && (item.zh_summary || item.summary || '').toLowerCase().indexOf(query) === -1) return false;
    if (cats.length > 0) {
      var hasCat = false;
      for (var ci = 0; ci < item.categories.length; ci++) {
        if (cats.indexOf(item.categories[ci]) !== -1) { hasCat = true; break; }
      }
      if (!hasCat) return false;
    }
    if (srcs.length > 0 && srcs.indexOf(item.source) === -1) return false;
    var dateFrom = document.getElementById('date-from').value;
    var dateTo = document.getElementById('date-to').value;
    var d = (item.published || '').slice(0, 10);
    if (dateFrom && d < dateFrom) return false;
    if (dateTo && d > dateTo) return false;
    return true;
  });

  if (sort === 'score-desc') {
    filtered.sort(function(a, b) { return (b.score || 0) - (a.score || 0); });
  } else if (sort === 'date-desc') {
    filtered.sort(function(a, b) { return (b.published || '').slice(0, 10).localeCompare((a.published || '').slice(0, 10)); });
  } else if (sort === 'date-asc') {
    filtered.sort(function(a, b) { return (a.published || '').slice(0, 10).localeCompare((b.published || '').slice(0, 10)); });
  }

  document.getElementById('result-count').textContent = '顯示 ' + filtered.length + ' / ' + DATA.length + ' 筆';

  var totalScore = 0;
  var uniqueSrcs = {};
  for (var fi = 0; fi < filtered.length; fi++) {
    totalScore += filtered[fi].score || 0;
    uniqueSrcs[filtered[fi].source] = true;
  }
  var srcCount = Object.keys(uniqueSrcs).length;
  document.getElementById('stats').innerHTML = ''
    + '<div class="stat-box"><div class="num">' + esc(filtered.length) + '</div><div class="label">篩選後</div></div>'
    + '<div class="stat-box"><div class="num">' + esc(srcCount) + '</div><div class="label">來源</div></div>'
    + '<div class="stat-box"><div class="num">' + esc(totalScore) + '</div><div class="label">總分</div></div>';

  if (group) {
    var byDate = {};
    for (var gi = 0; gi < filtered.length; gi++) {
      var d = (filtered[gi].published || '').slice(0, 10);
      if (!byDate[d]) byDate[d] = [];
      byDate[d].push(filtered[gi]);
    }
    var sortedDates = Object.keys(byDate).sort().reverse();
    var html = '';
    for (var di = 0; di < sortedDates.length; di++) {
      var date = sortedDates[di];
      var items = byDate[date];
      html += '<h3 class="date-heading">&#x1F4C5; ' + esc(date) + ' (' + items.length + ')</h3>';
      for (var ii = 0; ii < items.length; ii++) {
        html += cardHtml(items[ii]);
      }
    }
    document.getElementById('cards').innerHTML = html;
  } else {
    var flatHtml = '';
    for (var fi2 = 0; fi2 < filtered.length; fi2++) {
      flatHtml += cardHtml(filtered[fi2]);
    }
    document.getElementById('cards').innerHTML = flatHtml;
  }
}

render();
"""


def build_html(items: list[dict]) -> str:
    all_cats = sorted({c for i in items for c in i.get("categories", [])})
    all_sources = sorted({i.get("source", "") for i in items})

    cat_opts = "".join(
        f'<option value="{html.escape(c)}">{html.escape(c)}</option>' for c in all_cats
    )
    src_opts = "".join(
        f'<option value="{html.escape(s)}">{html.escape(s)}</option>' for s in all_sources
    )
    data_json = json.dumps(items, ensure_ascii=False)

    return (
        "<!DOCTYPE html>\n"
        '<html lang="zh-TW">\n'
        "<head>\n"
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Coffee Radar Dashboard</title>\n"
        "<style>\n" + CSS + "</style>\n"
        "</head>\n"
        "<body>\n"
        '<div class="container">\n'
        f"  <h1>Coffee Radar</h1>\n"
        f'  <div class="subtitle">{len(items)} 筆資料 · {len(all_cats)} 分類 · {len(all_sources)} 來源</div>\n'
        '\n'
        '  <div class="filters">\n'
        '    <input type="text" id="search" placeholder="搜尋標題或摘要..." oninput="render()">\n'
        '    <div class="filter-group">\n'
        '      <label>分類</label>\n'
        f'      <select id="cat-filter" multiple onchange="render()">{cat_opts}</select>\n'
        "    </div>\n"
        '    <div class="filter-group">\n'
        '      <label>來源</label>\n'
        f'      <select id="src-filter" multiple onchange="render()">{src_opts}</select>\n'
        "    </div>\n"
        '    <div class="filter-group">\n'
        '      <label>排序</label>\n'
        '      <select id="sort" onchange="render()">\n'
        '        <option value="date-desc">日期 ↓</option>\n'
        '        <option value="date-asc">日期 ↑</option>\n'
        '        <option value="score-desc">分數 ↓</option>\n'
        "      </select>\n"
        "    </div>\n"
        '    <div class="toggle-group">\n'
        '      <input type="checkbox" id="group-view" onchange="render()">\n'
        '      <label for="group-view">依日期分組</label>\n'
        "    </div>\n"
        '    <div class="filter-group">\n'
        '      <label>從</label>\n'
        '      <input type="date" id="date-from" onchange="render()">\n'
        "    </div>\n"
        '    <div class="filter-group">\n'
        '      <label>到</label>\n'
        '      <input type="date" id="date-to" onchange="render()">\n'
        "    </div>\n"
        "  </div>\n"
        '\n'
        '  <div class="stats" id="stats"></div>\n'
        '  <div id="result-count"></div>\n'
        '  <div id="cards"></div>\n'
        "</div>\n"
        '\n'
        f'<script id="app-data" type="application/json">{data_json}</script>\n'
        "<script>\n" + JS_SCRIPT + "</script>\n"
        "</body>\n"
        "</html>"
    )


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
    html_doc = build_html(items)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_doc, encoding="utf-8")
    print(f"Saved dashboard: {out.resolve()} ({len(html_doc)} bytes, {len(items)} items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
