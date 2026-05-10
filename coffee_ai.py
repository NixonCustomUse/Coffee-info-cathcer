#!/usr/bin/env python3
"""Chinese summaries and weekly synthesis for Coffee Radar."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from coffee_radar import clean_text

import config


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(items: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for item in items:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")


def extract_response_text(response: dict[str, Any]) -> str:
    for choice in response.get("choices", []):
        message = choice.get("message", {})
        content = message.get("content", "")
        if content:
            return content.strip()
    return ""


def openai_text(instructions: str, input_text: str, max_output_tokens: int = 700) -> str | None:
    if not config.LLM_API_KEY:
        return None

    payload = {
        "model": config.LLM_MODEL,
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": input_text},
        ],
        "max_tokens": max_output_tokens,
    }
    request = urllib.request.Request(
        config.LLM_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.LLM_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.LLM_TIMEOUT) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        print(f"OpenRouter API failed: HTTP {exc.code} {details}", file=sys.stderr)
        return None
    except urllib.error.URLError as exc:
        print(f"OpenRouter API failed: {exc}", file=sys.stderr)
        return None

    return extract_response_text(json.loads(raw))


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


def strip_feed_boilerplate(value: str) -> str:
    value = clean_text(value)
    value = value.split(" The post ", 1)[0]
    value = value.split(" appeared first on ", 1)[0]
    value = value.replace("Key takeaways ", "")
    value = re.sub(r"^Image: [^.]+\. ?", "", value)
    return value.strip()


def compact_signal_zh(item: dict[str, Any]) -> str:
    title = clean_text(item.get("title", ""))
    source = item.get("source", "未知來源")
    categories = "、".join(item.get("categories", [])) or "其他咖啡動態"
    terms = "、".join(item.get("matched_terms", [])[:4])
    summary = strip_feed_boilerplate(item.get("summary", ""))
    if summary:
        summary = textwrap.shorten(summary, width=120, placeholder="...")
        return f"{source} 的「{title}」顯示，這則訊號落在{categories}；{summary}"
    if terms:
        return f"{source} 的「{title}」值得追蹤，分類為{categories}，關鍵線索包括 {terms}。"
    return f"{source} 的「{title}」值得追蹤，分類為{categories}。"


def summarize_item_zh(item: dict[str, Any], use_ai: bool = True) -> str:
    if not use_ai:
        return fallback_summary_zh(item)

    instructions = (
        "你是咖啡產業研究助理。請用繁體中文整理咖啡產業文章摘要，"
        "語氣清楚、精煉、可供 Notion 資料庫快速閱讀。"
    )
    input_text = json.dumps(
        {
            "title": item.get("title", ""),
            "source": item.get("source", ""),
            "categories": item.get("categories", []),
            "matched_terms": item.get("matched_terms", []),
            "summary": item.get("summary", ""),
            "url": item.get("url", ""),
        },
        ensure_ascii=False,
    )
    prompt = (
        "請輸出 1 段繁體中文摘要，最多 90 字。"
        "要說明這篇對咖啡產業觀察的意義，不要誇大，不要加入原文沒有的事實。\n\n"
        f"{input_text}"
    )
    return openai_text(instructions, prompt, max_output_tokens=220) or fallback_summary_zh(item)


def enrich_items(items: list[dict[str, Any]], use_ai: bool = True, force: bool = False) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for item in items:
        next_item = dict(item)
        if force or not next_item.get("zh_summary"):
            next_item["zh_summary"] = summarize_item_zh(next_item, use_ai=use_ai)
        enriched.append(next_item)
    return enriched


def build_weekly_prompt(items: list[dict[str, Any]]) -> str:
    compact_items = [
        {
            "title": item.get("title", ""),
            "source": item.get("source", ""),
            "url": item.get("url", ""),
            "published": item.get("published", ""),
            "categories": item.get("categories", []),
            "score": item.get("score", 0),
            "summary": item.get("zh_summary") or item.get("summary", ""),
        }
        for item in items
    ]
    return json.dumps(compact_items, ensure_ascii=False)


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
    lines.extend(
        [
            "",
            "## 下週追蹤問題",
            "",
            "- 產地端：品種、土壤管理與氣候韌性是否有更多可量化成果？",
            "- 技術端：新設備是否真正降低人力、成本或品質波動？",
            "- 市場端：價格壓力會讓更多咖啡館嘗試自烘或改變採購策略嗎？",
        ]
    )
    return "\n".join(lines)


def pick_items(items: list[dict[str, Any]], categories: set[str]) -> list[dict[str, Any]]:
    picked = [
        item
        for item in items
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


def generate_weekly_article(items: list[dict[str, Any]], title: str, use_ai: bool = True) -> str:
    if not use_ai:
        return fallback_weekly_article(items, title)

    instructions = (
        "你是咖啡產業週報作者。請用繁體中文寫一篇清楚、可信、適合貼到 Notion 的週報。"
        "只能根據輸入資料整理，不要加入外部事實。"
    )
    prompt = (
        f"請根據以下 Coffee Radar 條目，寫一篇週報，標題為「{title}」。\n"
        "格式請使用 Markdown，包含：本週總覽、新研究與產地訊號、新技術與新產品、"
        "市場與商業變化、值得優先閱讀、下週追蹤問題。"
        "每個重要判斷都要能對應到文章標題。\n\n"
        f"{build_weekly_prompt(items)}"
    )
    return openai_text(instructions, prompt, max_output_tokens=1800) or fallback_weekly_article(items, title)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Add Chinese summaries to Coffee Radar JSONL.")
    parser.add_argument("--input", default="data/items.jsonl")
    parser.add_argument("--output", default="data/items.enriched.jsonl")
    parser.add_argument("--no-ai", action="store_true", help="Use deterministic fallback summaries.")
    parser.add_argument("--force", action="store_true", help="Regenerate existing zh_summary fields.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    items = load_jsonl(Path(args.input))
    enriched = enrich_items(items, use_ai=not args.no_ai, force=args.force)
    write_jsonl(enriched, Path(args.output))
    print(f"Saved {len(enriched)} enriched items to {args.output}")
    if not config.LLM_API_KEY and not args.no_ai:
        print("LLM_API_KEY is missing; used fallback Chinese summaries.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
