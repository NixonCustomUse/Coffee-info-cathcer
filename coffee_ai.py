#!/usr/bin/env python3
"""Chinese summaries for Coffee Radar — deterministic fallback only."""

from __future__ import annotations

import argparse
import textwrap
from pathlib import Path
from typing import Any

from coffee.util import (
    clean_text, load_jsonl, write_jsonl, strip_feed_boilerplate,
)


def fallback_summary_zh(item: dict[str, Any]) -> str:
    title = clean_text(item.get("title", ""))
    source = item.get("source", "未知來源")
    categories = "、".join(item.get("categories", [])) or "其他咖啡動態"
    summary = clean_text(item.get("summary", ""))
    if summary:
        summary = strip_feed_boilerplate(summary)
        summary = textwrap.shorten(summary, width=190, placeholder="...")
        return f"這篇來自 {source}，主題是「{title}」。目前歸類為{categories}。來源摘要重點：{summary}"
    return f"這篇來自 {source}，主題是「{title}」。目前歸類為{categories}，值得後續追蹤原文細節。"


def summarize_item_zh(item: dict[str, Any]) -> str:
    return fallback_summary_zh(item)


def enrich_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for item in items:
        next_item = dict(item)
        if not next_item.get("zh_summary"):
            next_item["zh_summary"] = summarize_item_zh(next_item)
        enriched.append(next_item)
    return enriched


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Add Chinese summaries to Coffee Radar JSONL.")
    parser.add_argument("--input", default="data/items.jsonl")
    parser.add_argument("--output", default="data/items.enriched.jsonl")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    items = load_jsonl(Path(args.input))
    enriched = enrich_items(items)
    write_jsonl(enriched, Path(args.output))
    print(f"Saved {len(enriched)} enriched items to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
