#!/usr/bin/env python3
"""Generate weekly Coffee Radar articles."""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
from pathlib import Path
from typing import Any

from coffee.util import UTC, parse_date, load_jsonl, compact_signal_zh


def item_date(item: dict[str, Any]) -> dt.date | None:
    parsed = parse_date(item.get("published", ""))
    return parsed.date() if parsed else None


def select_recent_items(
    items: list[dict[str, Any]], days: int, now: dt.datetime | None = None,
) -> list[dict[str, Any]]:
    now = now or dt.datetime.now(UTC)
    cutoff = (now - dt.timedelta(days=days)).date()
    recent = [item for item in items if (item_date(item) or dt.date.min) >= cutoff]
    if recent:
        return sorted(recent, key=lambda item: (item.get("score", 0), item.get("published", "")), reverse=True)
    return sorted(items, key=lambda item: item.get("score", 0), reverse=True)[:20]


def pick_items(items: list[dict[str, Any]], categories: set[str]) -> list[dict[str, Any]]:
    picked = [
        item for item in items
        if categories.intersection(set(item.get("categories", [])))
    ]
    return sorted(picked, key=lambda item: item.get("score", 0), reverse=True)


def format_category_counts(category_counts: dict[str, int]) -> str:
    if not category_counts:
        return "少量分散主題"
    pairs = sorted(category_counts.items(), key=lambda pair: pair[1], reverse=True)[:4]
    return "、".join(f"{category} {count} 則" for category, count in pairs)


def render_item_paragraph(items: list[dict[str, Any]], lead: str) -> str:
    if not items:
        return "本週沒有明顯訊號。"
    fragments = []
    for item in items:
        summary = item.get("zh_summary") if item.get("zh_summary") and "這篇來自" not in item.get("zh_summary", "") else compact_signal_zh(item)
        fragments.append(summary)
    return lead + "：" + "；".join(fragments) + "。"


def generate_weekly_article(items: list[dict[str, Any]], title: str) -> str:
    return fallback_weekly_article(items, title)


def fallback_weekly_article(items: list[dict[str, Any]], title: str) -> str:
    category_counts: dict[str, int] = {}
    for item in items:
        for category in item.get("categories", []):
            category_counts[category] = category_counts.get(category, 0) + 1

    research = pick_items(items, {"種植/氣候", "農場/產地"})
    technology = pick_items(items, {"烘焙/萃取技術", "設備/自動化"})
    market = pick_items(items, {"市場/價格"})
    top_items = sorted(items, key=lambda item: item.get("score", 0), reverse=True)[:5]

    lines = [
        f"# {title}",
        "",
        "## 本週總覽",
        "",
        f"本週 Coffee Radar 收錄 {len(items)} 則咖啡產業訊號。"
        f"主要集中在{format_category_counts(category_counts)}。"
        "整體來看，值得注意的是產地端的品種與氣候韌性、咖啡館端的效率工具，以及市場成本壓力如何推動經營模式改變。",
        "",
        "## 新研究與產地訊號",
        "",
        render_item_paragraph(research[:4], "本週研究與產地端的重點包含"),
        "",
        "## 新技術與新產品",
        "",
        render_item_paragraph(technology[:4], "技術與設備端值得追蹤的內容包含"),
        "",
        "## 市場與商業變化",
        "",
        render_item_paragraph(market[:4], "市場面主要可以看到"),
        "",
        "## 值得優先閱讀",
        "",
    ]
    for item in top_items:
        summary = item.get("zh_summary") if item.get("zh_summary") and "這篇來自" not in item.get("zh_summary", "") else compact_signal_zh(item)
        lines.append(f"- [{item.get('title')}]({item.get('url')}) — {summary}")
    lines.extend([
        "",
        "## 下週追蹤問題",
        "",
        "- 產地端：品種、土壤管理與氣候韌性是否有更多可量化成果？",
        "- 技術端：新設備是否真正降低人力、成本或品質波動？",
        "- 市場端：價格壓力會讓更多咖啡館嘗試自烘或改變採購策略嗎？",
    ])
    return "\n".join(lines)


def week_title(now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now()
    year, week, _ = now.isocalendar()
    return f"Coffee Radar 週報：{year}-W{week:02d}"


def output_paths(output_dir: Path, now: dt.datetime | None = None) -> tuple[Path, Path]:
    now = now or dt.datetime.now()
    year, week, _ = now.isocalendar()
    dated = output_dir / f"{year}-W{week:02d}.md"
    latest = output_dir / "latest.md"
    return dated, latest


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a weekly Coffee Radar article.")
    parser.add_argument("--input", default="data/items.enriched.jsonl")
    parser.add_argument("--output-dir", default="reports/weekly")
    parser.add_argument("--days", type=int, default=7)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    items = load_jsonl(Path(args.input))
    selected = select_recent_items(items, days=args.days)
    title = week_title()
    article = generate_weekly_article(selected, title=title)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    dated, latest = output_paths(output_dir)
    dated.write_text(article, encoding="utf-8")
    shutil.copyfile(dated, latest)
    print(f"Saved weekly article to {dated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
