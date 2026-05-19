#!/usr/bin/env python3
"""Coffee Radar: collect and classify coffee industry signals."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from coffee import (
    Source, Item, load_sources, classify, is_recent, is_relevant_item,
    dedupe, sort_key, item_to_dict, write_jsonl, fetch_json, fetch_text,
    parse_crossref, parse_europe_pmc, parse_feed, parse_page, parse_reddit,
    write_markdown, write_segment_reports,
)


def collect(
    sources: list[Source], days: int, minimum_score: int,
) -> tuple[list[Item], list[str]]:
    items: list[Item] = []
    errors: list[str] = []
    total_sources = len(sources)
    is_tty = sys.stderr.isatty()

    for index, source in enumerate(sources, start=1):
        kept_count = 0
        try:
            if source.kind == "crossref":
                parsed_items = parse_crossref(source, fetch_json(source.url))
            elif source.kind == "europe_pmc":
                parsed_items = parse_europe_pmc(source, fetch_json(source.url))
            elif source.kind == "reddit":
                content = fetch_text(source.url)
                parsed_items = parse_reddit(source, content)
            else:
                content = fetch_text(source.url)
                parsed_items = (
                    parse_page(source, content)
                    if source.kind == "page"
                    else parse_feed(source, content)
                )
        except Exception as exc:
            errors.append(f"{source.name}: {exc}")
            status = "FAIL"
        else:
            status = "OK"
            for item in parsed_items:
                if not is_relevant_item(source, item):
                    continue
                classified = classify(item)
                if classified.score >= minimum_score and is_recent(classified.published, days):
                    items.append(classified)
                    kept_count += 1

        width = 24
        done = int((index / total_sources) * width)
        bar = "#" * done + "-" * (width - done)
        label = (source.name[:25] + "...") if len(source.name) > 26 else source.name
        line = (
            f"[{bar}] {index:>2}/{total_sources} | {label:<26} | {status:<4} "
            f"| kept={kept_count:>3} | fail={len(errors):>2}"
        )
        end = "\r" if is_tty and index < total_sources else "\n"
        print(line, end=end, file=sys.stderr, flush=True)

    items = dedupe(items)
    return sorted(items, key=sort_key, reverse=True), errors


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect coffee industry signals from RSS feeds and public pages."
    )
    parser.add_argument("--sources", default="sources.json", help="Path to source config JSON.")
    parser.add_argument("--days", type=int, default=45, help="Keep items from the last N days.")
    parser.add_argument("--limit", type=int, default=30, help="Maximum items in the Markdown report.")
    parser.add_argument(
        "--min-score", type=int, default=2,
        help="Minimum keyword score. Raise this to make the report stricter.",
    )
    parser.add_argument("--out", default="reports/latest.md", help="Markdown output path.")
    parser.add_argument("--jsonl", default="data/items.jsonl", help="Raw JSONL output path.")
    parser.add_argument(
        "--segment-dir", default="reports/segments",
        help="Directory for farm/processing/climate-tech/equipment reports.",
    )
    parser.add_argument("--no-segments", action="store_true", help="Do not write segment reports.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    source_path = Path(args.sources)
    sources = load_sources(source_path)
    items, errors = collect(sources, days=args.days, minimum_score=args.min_score)
    write_markdown(items, errors, Path(args.out), limit=args.limit)
    write_jsonl([item_to_dict(i) for i in items], Path(args.jsonl))
    if not args.no_segments:
        write_segment_reports(items, Path(args.segment_dir), limit=args.limit)

    print(f"Saved {min(len(items), args.limit)} report items to {args.out}")
    print(f"Saved {len(items)} raw items to {args.jsonl}")
    if not args.no_segments:
        print(f"Saved segment reports to {args.segment_dir}")
    if errors:
        print(f"{len(errors)} source(s) failed. See report for details.", file=sys.stderr)
    return 0 if items else 2


if __name__ == "__main__":
    raise SystemExit(main())
