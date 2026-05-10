#!/usr/bin/env python3
"""Sync Coffee Radar items and weekly articles to Notion with URL dedupe."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from coffee_ai import load_jsonl
from coffee_radar import UTC, normalize_url, parse_date
import config


@dataclass
class NotionConfig:
    articles_database_id: str = ""
    sources_database_id: str = ""
    weekly_parent_page_id: str = ""


class SyncState:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS synced_urls (
                url TEXT PRIMARY KEY,
                notion_page_id TEXT,
                title TEXT,
                synced_at TEXT
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS synced_weekly_reports (
                title TEXT PRIMARY KEY,
                notion_page_id TEXT,
                synced_at TEXT
            )
            """
        )
        self.connection.commit()

    def has_url(self, url: str) -> bool:
        key = normalize_url(url)
        row = self.connection.execute("SELECT 1 FROM synced_urls WHERE url = ?", (key,)).fetchone()
        return row is not None

    def mark_url(self, url: str, notion_page_id: str, title: str) -> None:
        key = normalize_url(url)
        self.connection.execute(
            """
            INSERT OR REPLACE INTO synced_urls (url, notion_page_id, title, synced_at)
            VALUES (?, ?, ?, ?)
            """,
            (key, notion_page_id, title, dt.datetime.now(UTC).isoformat()),
        )
        self.connection.commit()

    def has_weekly_report(self, title: str) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM synced_weekly_reports WHERE title = ?", (title,)
        ).fetchone()
        return row is not None

    def mark_weekly_report(self, title: str, notion_page_id: str) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO synced_weekly_reports (title, notion_page_id, synced_at)
            VALUES (?, ?, ?)
            """,
            (title, notion_page_id, dt.datetime.now(UTC).isoformat()),
        )
        self.connection.commit()


def load_config(path: Path) -> NotionConfig:
    data: dict[str, str] = {}
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    return NotionConfig(
        articles_database_id=config.NOTION_ARTICLES_DATABASE_ID or data.get("articles_database_id", ""),
        sources_database_id=config.NOTION_SOURCES_DATABASE_ID or data.get("sources_database_id", ""),
        weekly_parent_page_id=config.NOTION_WEEKLY_PARENT_PAGE_ID or data.get("weekly_parent_page_id", ""),
    )


def notion_request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not config.NOTION_TOKEN:
        raise RuntimeError("NOTION_TOKEN is missing.")

    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"https://api.notion.com/v1/{path.lstrip('/')}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {config.NOTION_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": config.NOTION_VERSION,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Notion API failed: HTTP {exc.code} {details}") from exc
    return json.loads(raw) if raw else {}


def truncate(value: str, limit: int = 1900) -> str:
    return value if len(value) <= limit else value[: limit - 1] + "…"


def rich_text(value: str) -> list[dict[str, Any]]:
    return [{"text": {"content": truncate(value)}}] if value else []


def item_date_iso(item: dict[str, Any]) -> str | None:
    parsed = parse_date(item.get("published", ""))
    return parsed.date().isoformat() if parsed else None


def notion_page_exists(database_id: str, url: str) -> str | None:
    payload = {
        "filter": {
            "property": "網址",
            "url": {"equals": url},
        },
        "page_size": 1,
    }
    result = notion_request("POST", f"databases/{database_id}/query", payload)
    results = result.get("results", [])
    return results[0].get("id") if results else None


def item_properties(item: dict[str, Any]) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "文章": {"title": rich_text(item.get("title", ""))},
        "來源": {"select": {"name": item.get("source", "未知來源")}},
        "網址": {"url": item.get("url", "")},
        "分類": {"multi_select": [{"name": category} for category in item.get("categories", [])]},
        "命中線索": {"rich_text": rich_text(", ".join(item.get("matched_terms", [])))},
        "摘要": {"rich_text": rich_text(item.get("zh_summary") or item.get("summary", ""))},
        "分數": {"number": item.get("score", 0)},
        "狀態": {"select": {"name": "New"}},
    }
    published = item_date_iso(item)
    if published:
        properties["發布日期"] = {"date": {"start": published}}
    return properties


def paragraph(text: str) -> dict[str, Any]:
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": rich_text(text)}}


def heading(text: str, level: int = 2) -> dict[str, Any]:
    block_type = f"heading_{level}"
    return {"object": "block", "type": block_type, block_type: {"rich_text": rich_text(text)}}


def item_children(item: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        heading("中文摘要", 2),
        paragraph(item.get("zh_summary") or item.get("summary", "") or "尚無摘要。"),
        heading("線索", 2),
        paragraph(", ".join(item.get("matched_terms", [])) or "尚無命中線索。"),
        paragraph(f"原文：{item.get('url', '')}"),
    ]


def create_item_page(database_id: str, item: dict[str, Any]) -> str:
    payload = {
        "parent": {"database_id": database_id},
        "properties": item_properties(item),
        "children": item_children(item),
    }
    result = notion_request("POST", "pages", payload)
    return result.get("id", "")


def sync_items(
    items: list[dict[str, Any]],
    config: NotionConfig,
    state: SyncState,
    limit: int,
    check_notion: bool,
    dry_run: bool,
) -> tuple[int, int]:
    if not config.articles_database_id:
        raise RuntimeError("Notion articles database ID is missing.")

    created = 0
    skipped = 0
    for item in items[:limit]:
        url = item.get("url", "")
        if not url:
            skipped += 1
            continue
        if state.has_url(url):
            skipped += 1
            continue
        if check_notion and not dry_run:
            existing_id = notion_page_exists(config.articles_database_id, url)
            if existing_id:
                state.mark_url(url, existing_id, item.get("title", ""))
                skipped += 1
                continue
        if dry_run:
            print(f"Would sync: {item.get('title')} ({url})")
            created += 1
            continue
        page_id = create_item_page(config.articles_database_id, item)
        state.mark_url(url, page_id, item.get("title", ""))
        created += 1
    return created, skipped


def markdown_blocks(markdown: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("### "):
            blocks.append(heading(line[4:], 3))
        elif line.startswith("## "):
            blocks.append(heading(line[3:], 2))
        elif line.startswith("# "):
            blocks.append(heading(line[2:], 1))
        elif line.startswith("- "):
            blocks.append(
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": rich_text(line[2:])},
                }
            )
        else:
            blocks.append(paragraph(line))
    return blocks[:95]


def sync_weekly_report(markdown_path: Path, config: NotionConfig, state: SyncState, dry_run: bool) -> bool:
    if not config.weekly_parent_page_id:
        raise RuntimeError("Notion weekly parent page ID is missing.")
    markdown = markdown_path.read_text(encoding="utf-8")
    title = next((line[2:].strip() for line in markdown.splitlines() if line.startswith("# ")), markdown_path.stem)
    if state.has_weekly_report(title):
        return False
    if dry_run:
        print(f"Would sync weekly report: {title}")
        return True
    payload = {
        "parent": {"page_id": config.weekly_parent_page_id},
        "properties": {"title": [{"text": {"content": title}}]},
        "children": markdown_blocks(markdown),
        "icon": {"emoji": "☕"},
    }
    result = notion_request("POST", "pages", payload)
    state.mark_weekly_report(title, result.get("id", ""))
    return True


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync Coffee Radar data to Notion.")
    parser.add_argument("--items", default="data/items.enriched.jsonl")
    parser.add_argument("--config", default="notion_config.json")
    parser.add_argument("--state", default="data/sync_state.sqlite")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-notion-check", action="store_true")
    parser.add_argument("--sync-weekly", help="Path to a weekly Markdown report to add as a Notion page.")
    parser.add_argument(
        "--skip-notion-if-unconfigured",
        action="store_true",
        help="Exit cleanly when NOTION_TOKEN is missing.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if not config.NOTION_TOKEN and not args.dry_run:
        message = "NOTION_TOKEN is missing; skipped Notion sync."
        if args.skip_notion_if_unconfigured:
            print(message)
            return 0
        print(message, file=sys.stderr)
        return 3

    config = load_config(Path(args.config))
    state = SyncState(Path(args.state))
    items = load_jsonl(Path(args.items))
    created, skipped = sync_items(
        items,
        config=config,
        state=state,
        limit=args.limit,
        check_notion=not args.no_notion_check,
        dry_run=args.dry_run,
    )
    print(f"Article sync complete: {created} created, {skipped} skipped.")
    if args.sync_weekly:
        synced = sync_weekly_report(Path(args.sync_weekly), config=config, state=state, dry_run=args.dry_run)
        print("Weekly report synced." if synced else "Weekly report already synced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
