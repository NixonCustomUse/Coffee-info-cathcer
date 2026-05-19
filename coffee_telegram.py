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
    row = []
    for i, item in enumerate(items):
        url = item.get("url", "")
        title = item.get("title", "")
        if url:
            label = f"{i + 1}. {title[:60]}"
            row.append({"text": label, "url": url})
            if len(row) == 2:
                keyboard.append(row)
                row = []
    if row:
        keyboard.append(row)
    return keyboard


def build_daily_body(items: list[dict], limit: int = 5) -> tuple[str, list[list[dict]]]:
    yesterday = dt.datetime.now(UTC).date() - dt.timedelta(days=1)

    filtered = []
    for i in items:
        pub = parse_date(i.get("published", ""))
        if pub and pub.date() == yesterday:
            filtered.append(i)

    if not filtered:
        return (
            f"☕ 咖啡日報 — {yesterday}\n"
            f"─────────────────\n"
            f"昨天沒有新訊號。",
            [],
        )

    top = sorted(filtered, key=lambda i: i.get("score", 0), reverse=True)[:limit]
    cats = Counter()
    for i in filtered:
        for c in i.get("categories", []):
            cats[c] += 1
    cat_summary = "、".join(f"{c}({n})" for c, n in cats.most_common())

    lines = [
        f"☕ 咖啡日報 — {yesterday}",
        f"─────────────────",
        f"昨天共 {len(filtered)} 則咖啡訊號",
        "",
        f"分類：{cat_summary}",
        "",
    ]

    for i, item in enumerate(top, 1):
        title = item.get("title", "")
        source = item.get("source", "")
        categories = "、".join(item.get("categories", []))
        summary = (item.get("zh_summary", "") or "").strip()
        lines.append(f"{i}. {title}")
        lines.append(f"   {source} · {categories}")
        if summary:
            short = summary[:100] + "…" if len(summary) > 100 else summary
            lines.append(f"   {short}")

    keyboard = build_keyboard(top)
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
    parser.add_argument("--token", help="Bot token (or TELEGRAM_BOT_TOKEN env)")
    parser.add_argument("--chat-id", help="Chat ID (or TELEGRAM_CHAT_ID env)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    items = load_jsonl(Path(args.input))
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
