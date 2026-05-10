#!/usr/bin/env python3
"""Generate a standalone HTML report from JSONL data."""

from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def shorten(text: str, width: int = 200) -> str:
    return textwrap.shorten(text, width=width, placeholder="...") if text else ""


def build_html(items: list[dict[str, Any]]) -> str:
    category_counts: dict[str, int] = {}
    for item in items:
        for c in item.get("categories", []):
            category_counts[c] = category_counts.get(c, 0) + 1

    cat_badges = "".join(
        f'<span class="badge">{c} ({n})</span>'
        for c, n in sorted(category_counts.items(), key=lambda x: -x[1])
    )

    item_cards = ""
    for i, item in enumerate(items, 1):
        cats = "".join(f'<span class="tag">{c}</span>' for c in item.get("categories", []))
        terms = " ".join(f'<span class="term">{t}</span>' for t in item.get("matched_terms", [])[:6])
        summary = item.get("zh_summary") or item.get("summary", "")
        published = item.get("published", "N/A")[:10]
        score = item.get("score", 0)

        item_cards += f"""
        <div class="card">
          <div class="card-header">
            <span class="score">{score}</span>
            <a href="{item.get('url', '#')}" target="_blank" class="title">{item.get('title', 'Untitled')}</a>
          </div>
          <div class="meta">
            <span class="source">{item.get('source', 'Unknown')}</span>
            <span class="date">{published}</span>
          </div>
          <div class="cats">{cats}</div>
          <div class="summary">{shorten(summary, 300)}</div>
          <div class="terms">{terms}</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Coffee Info Catcher Report</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f5f5f0; color: #2c2c2c; padding: 24px; line-height: 1.6;
  }}
  .container {{ max-width: 900px; margin: 0 auto; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 4px; color: #1a1a1a; }}
  .subtitle {{ color: #666; font-size: 0.9rem; margin-bottom: 20px; }}
  .stats {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }}
  .stat-box {{
    background: #fff; padding: 12px 18px; border-radius: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06); flex: 1; min-width: 100px;
  }}
  .stat-box .num {{ font-size: 1.4rem; font-weight: 700; color: #1a1a1a; }}
  .stat-box .label {{ font-size: 0.75rem; color: #888; text-transform: uppercase; }}
  .badges {{ display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 24px; }}
  .badge {{
    background: #e8e8e0; padding: 4px 12px; border-radius: 20px;
    font-size: 0.8rem; color: #555;
  }}
  .card {{
    background: #fff; border-radius: 12px; padding: 18px 20px;
    margin-bottom: 12px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    transition: box-shadow 0.15s;
  }}
  .card:hover {{ box-shadow: 0 2px 12px rgba(0,0,0,0.1); }}
  .card-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }}
  .score {{
    background: #1a1a1a; color: #fff; font-size: 0.7rem; font-weight: 700;
    width: 24px; height: 24px; border-radius: 6px; display: flex;
    align-items: center; justify-content: center; flex-shrink: 0;
  }}
  .title {{ font-weight: 600; color: #1a1a1a; text-decoration: none; font-size: 0.95rem; }}
  .title:hover {{ text-decoration: underline; }}
  .meta {{ display: flex; gap: 12px; font-size: 0.8rem; color: #888; margin-bottom: 8px; }}
  .source {{ font-weight: 500; }}
  .cats {{ display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 8px; }}
  .tag {{
    background: #f0efe8; padding: 2px 10px; border-radius: 12px;
    font-size: 0.75rem; color: #666;
  }}
  .summary {{ font-size: 0.88rem; color: #444; margin-bottom: 8px; }}
  .terms {{ display: flex; gap: 4px; flex-wrap: wrap; }}
  .term {{
    background: #f5f5f0; border: 1px solid #e0e0d8; padding: 1px 8px;
    border-radius: 4px; font-size: 0.7rem; color: #999;
  }}
  @media (max-width: 600px) {{
    body {{ padding: 12px; }}
    .stat-box {{ min-width: 80px; padding: 10px 14px; }}
  }}
</style>
</head>
<body>
<div class="container">
  <h1>Coffee Info Catcher</h1>
  <div class="subtitle">{len(items)} items &middot; {len(category_counts)} categories</div>

  <div class="stats">
    <div class="stat-box"><div class="num">{len(items)}</div><div class="label">Items</div></div>
    <div class="stat-box"><div class="num">{len(set(i.get('source','') for i in items))}</div><div class="label">Sources</div></div>
    <div class="stat-box"><div class="num">{sum(i.get('score',0) for i in items)}</div><div class="label">Total Score</div></div>
    <div class="stat-box"><div class="num">{sum(len(i.get('categories',[])) for i in items) / max(len(items),1):.1f}</div><div class="label">Avg Cats</div></div>
  </div>

  <div class="badges">{cat_badges}</div>

  {item_cards}
</div>
</body>
</html>"""


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate HTML report from JSONL data.")
    parser.add_argument("--input", default="data/items.jsonl")
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
    print(f"Saved report: {out.resolve()} ({len(html)} bytes, {len(items)} items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
