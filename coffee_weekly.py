#!/usr/bin/env python3
"""Generate weekly Coffee Radar articles."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
from pathlib import Path
from typing import Any

from coffee_ai import generate_weekly_article, load_jsonl
from coffee_radar import UTC, parse_date
import config


def item_date(item: dict[str, Any]) -> dt.date | None:
    parsed = parse_date(item.get("published", ""))
    return parsed.date() if parsed else None


def select_recent_items(
    items: list[dict[str, Any]],
    days: int,
    now: dt.datetime | None = None,
) -> list[dict[str, Any]]:
    now = now or dt.datetime.now(UTC)
    cutoff = (now - dt.timedelta(days=days)).date()
    recent = [item for item in items if (item_date(item) or dt.date.min) >= cutoff]
    if recent:
        return sorted(recent, key=lambda item: (item.get("score", 0), item.get("published", "")), reverse=True)
    return sorted(items, key=lambda item: item.get("score", 0), reverse=True)[:20]


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
    parser.add_argument("--no-ai", action="store_true", help="Use deterministic fallback writing.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    items = load_jsonl(Path(args.input))
    selected = select_recent_items(items, days=args.days)
    title = week_title()
    article = generate_weekly_article(selected, title=title, use_ai=not args.no_ai)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    dated, latest = output_paths(output_dir)
    dated.write_text(article, encoding="utf-8")
    shutil.copyfile(dated, latest)
    print(f"Saved weekly article to {dated}")
    if not config.LLM_API_KEY and not args.no_ai:
        print("LLM_API_KEY is missing; used fallback weekly article.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
