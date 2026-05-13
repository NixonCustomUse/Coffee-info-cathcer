from __future__ import annotations

import datetime as dt
import email.utils
import html
import json
import re
import textwrap
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


USER_AGENT = (
    "Mozilla/5.0 (compatible; CoffeeRadar/0.1; "
    "+https://example.local/coffee-radar)"
)
UTC = dt.timezone.utc


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def parse_date(value: str) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        parsed = None
    if parsed:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), parsed.query, "")
    )


def fetch_text(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def fetch_json(url: str, timeout: int = 20) -> dict[str, object]:
    return json.loads(fetch_text(url, timeout=timeout))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(items: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for item in items:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")


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
