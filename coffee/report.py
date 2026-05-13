from __future__ import annotations

import datetime as dt
import json
import sys
import textwrap
from pathlib import Path
from typing import Iterable

from coffee.util import UTC
from coffee.classify import Item, item_matches_segment, item_to_dict, SEGMENT_DEFINITIONS


def truncate_label(value: str, max_length: int = 26) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 1] + "…"


def progress_line(
    index: int, total: int, source_name: str, status: str,
    kept_items: int, failures: int,
) -> str:
    width = 24
    done = int((index / total) * width)
    bar = "#" * done + "-" * (width - done)
    label = truncate_label(source_name)
    return (
        f"[{bar}] {index:>2}/{total} | {label:<26} | {status:<4} "
        f"| kept={kept_items:>3} | fail={failures:>2}"
    )


def write_markdown(items: list[Item], errors: list[str], path: Path, limit: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    generated = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    visible_items = items[:limit]
    category_counts: dict[str, int] = {}
    for item in visible_items:
        for category in item.categories:
            category_counts[category] = category_counts.get(category, 0) + 1

    lines = [
        "# Coffee Radar Report",
        "",
        f"產生時間：{generated}",
        f"收錄項目：{len(visible_items)} / {len(items)}",
        "",
        "## 分類概覽",
        "",
    ]

    if category_counts:
        for category, count in sorted(category_counts.items(), key=lambda pair: pair[0]):
            lines.append(f"- {category}: {count}")
    else:
        lines.append("- 暫時沒有符合條件的項目")

    lines.extend(["", "## 觀測項目", ""])

    for index, item in enumerate(visible_items, start=1):
        categories = "、".join(item.categories)
        terms = "、".join(item.matched_terms[:8]) or "來源相關"
        published = item.published or "未標示"
        summary = textwrap.shorten(item.summary, width=320, placeholder="...") if item.summary else ""
        lines.extend([
            f"### {index}. [{item.title}]({item.url})",
            "",
            f"- 來源：{item.source}",
            f"- 日期：{published}",
            f"- 分類：{categories}",
            f"- 命中線索：{terms}",
        ])
        if summary:
            lines.append(f"- 摘要：{summary}")
        lines.append("")

    if errors:
        lines.extend(["## 抓取失敗來源", ""])
        lines.extend(f"- {error}" for error in errors)
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_segment_reports(items: list[Item], output_dir: Path, limit: int) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    index_lines = ["# Coffee Radar 分眾報告", ""]
    for slug, segment in SEGMENT_DEFINITIONS.items():
        segment_items = [item for item in items if item_matches_segment(item, segment)]
        report_path = output_dir / f"{slug}.md"
        write_segment_report(segment_items, report_path, segment, limit)
        index_lines.append(f"- [{segment['title']}]({slug}.md): {len(segment_items)} 則")
    (output_dir / "index.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")


def write_segment_report(
    items: list[Item], path: Path, segment: dict[str, object], limit: int,
) -> None:
    generated = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    visible_items = items[:limit]
    lines = [
        f"# {segment['title']}",
        "",
        f"產生時間：{generated}",
        f"收錄項目：{len(visible_items)} / {len(items)}",
        "",
        str(segment["description"]),
        "",
        "## 重點項目",
        "",
    ]
    if not visible_items:
        lines.append("暫時沒有符合這個分眾報告的項目。")
    for index, item in enumerate(visible_items, start=1):
        categories = "、".join(item.categories)
        terms = "、".join(item.matched_terms[:8]) or "來源相關"
        summary = textwrap.shorten(item.summary, width=260, placeholder="...") if item.summary else ""
        lines.extend([
            f"### {index}. [{item.title}]({item.url})",
            "",
            f"- 來源：{item.source}",
            f"- 日期：{item.published or '未標示'}",
            f"- 分類：{categories}",
            f"- 命中線索：{terms}",
        ])
        if summary:
            lines.append(f"- 摘要：{summary}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
