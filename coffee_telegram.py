#!/usr/bin/env python3
"""Send Coffee Radar daily report via Telegram."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.request
from collections import Counter
from pathlib import Path

from coffee.util import UTC, load_jsonl, parse_date


def build_keyboard(items: list[dict]) -> list[list[dict]]:
    keyboard = []
    for item in items:
        url = item.get("url", "")
        source = item.get("source", "")
        if url:
            keyboard.append([{"text": source[:40], "url": url}])
    return keyboard


def build_daily_body(items: list[dict], limit: int = 5) -> tuple[str, list[list[dict]]]:
    now = dt.datetime.now(UTC).date()
    week_ago = now - dt.timedelta(days=7)

    filtered = []
    for i in items:
        pub = parse_date(i.get("published", ""))
        if pub and week_ago <= pub.date() <= now:
            filtered.append(i)

    if not filtered:
        return (
            f"☕ 咖啡日報 — {now.month}/{now.day}\n"
            f"────────────────\n"
            f"過去 7 天沒有新訊號。",
            [],
        )

    top = sorted(filtered, key=lambda i: i.get("score", 0), reverse=True)[:limit]
    cats = Counter()
    for i in filtered:
        for c in i.get("categories", []):
            cats[c] += 1
    cat_summary = " · ".join(f"{c}({n})" for c, n in cats.most_common())

    sources = len({i.get("source", "") for i in filtered})

    lines = [
        f"☕ 咖啡週報 — {now.month}/{now.day}",
        f"────────────────",
        f"{len(filtered)} 則 | {sources} 來源 | {cat_summary}",
        "",
    ]

    for item in top:
        title = item.get("title", "")
        source = item.get("source", "")
        lines.append(f"<b>{source}</b>")
        lines.append(title)
        lines.append("")

    keyboard = build_keyboard(top)
    return "\n".join(lines), keyboard


def build_digest_body(items: list[dict], limit: int = 3) -> tuple[str, list[list[dict]]]:
    now = dt.datetime.now(UTC)
    monday = now - dt.timedelta(days=now.weekday())
    sunday = monday + dt.timedelta(days=6)

    filtered = []
    for i in items:
        pub = parse_date(i.get("published", ""))
        if pub and monday.date() <= pub.date() <= sunday.date():
            filtered.append(i)

    if not filtered:
        return (
            f"☕ 本週精選 — W{now.isocalendar()[1]}\n"
            f"────────────────\n"
            f"本週沒有新訊號。",
            [],
        )

    by_date: dict[dt.date, list[dict]] = {}
    for i in filtered:
        pub = parse_date(i.get("published", ""))
        if pub:
            by_date.setdefault(pub.date(), []).append(i)

    cats = Counter()
    for i in filtered:
        for c in i.get("categories", []):
            cats[c] += 1
    cat_summary = " · ".join(f"{c}({n})" for c, n in cats.most_common())

    sources = len({i.get("source", "") for i in filtered})

    lines = [
        f"☕ 本週精選 — W{now.isocalendar()[1]}",
        f"────────────────",
        f"{len(filtered)} 則 · {sources} 來源 | {cat_summary}",
        "",
    ]

    weekday_zh = ["(一)", "(二)", "(三)", "(四)", "(五)", "(六)", "(日)"]

    all_top_items: list[dict] = []
    for date in sorted(by_date.keys(), reverse=True):
        day_items = sorted(by_date[date], key=lambda i: i.get("score", 0), reverse=True)[:limit]
        lines.append(f"📅 {date.month}/{date.day} {weekday_zh[date.weekday()]}")
        for item in day_items:
            title = item.get("title", "")
            source = item.get("source", "")
            lines.append(f"<b>{source}</b>")
            lines.append(title)
            lines.append("")
        all_top_items.extend(day_items)

    keyboard = build_keyboard(all_top_items)
    return "\n".join(lines), keyboard


def send_telegram(
    text: str, token: str, chat_id: str,
    keyboard: list[list[dict]] | None = None,
) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload: dict[str, object] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if keyboard:
        payload["reply_markup"] = {"inline_keyboard": keyboard}

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception as exc:
        print(f"Telegram send failed: {exc}", file=sys.stderr)
        return False


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send Coffee Radar daily report to Telegram.")
    parser.add_argument("--input", default="data/items.enriched.jsonl")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--digest", action="store_true", help="Generate weekly digest instead of daily report")
    parser.add_argument("--token", help="Bot token (or TELEGRAM_BOT_TOKEN env)")
    parser.add_argument("--chat-id", help="Chat ID (or TELEGRAM_CHAT_ID env)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    items = load_jsonl(Path(args.input))

    if args.digest:
        text, keyboard = build_digest_body(items, limit=args.limit)
    else:
        text, keyboard = build_daily_body(items, limit=args.limit)

    if args.dry_run:
        print(text)
        if keyboard:
            print("\n--- keyboard ---")
            print(json.dumps(keyboard, ensure_ascii=False, indent=2))
        return 0

    token = args.token or os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = args.chat_id or os.getenv("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID", file=sys.stderr)
        return 1

    ok = send_telegram(text, token, chat_id, keyboard=keyboard)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
