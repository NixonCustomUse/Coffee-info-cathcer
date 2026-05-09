#!/usr/bin/env python3
"""Coffee Radar: collect and classify coffee industry signals."""

from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import html
import json
import re
import sys
import textwrap
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


USER_AGENT = (
    "Mozilla/5.0 (compatible; CoffeeRadar/0.1; "
    "+https://example.local/coffee-radar)"
)
UTC = dt.timezone.utc

CATEGORY_KEYWORDS = {
    "農場/產地": [
        "farm",
        "farms",
        "farmer",
        "farmers",
        "producer",
        "producers",
        "origin",
        "estate",
        "cooperative",
        "smallholder",
        "finca",
        "plantation",
        "harvest",
        "terroir",
        "traceability",
        "single origin",
        "arabica",
        "robusta",
        "geisha",
        "gesha",
        "農場",
        "產地",
        "莊園",
        "小農",
    ],
    "種植/氣候": [
        "climate",
        "agroforestry",
        "shade",
        "irrigation",
        "soil",
        "drought",
        "leaf rust",
        "disease",
        "pest",
        "replanting",
        "seedling",
        "breeding",
        "variety",
        "resilience",
        "sustainability",
        "climate-smart",
        "氣候",
        "育種",
        "品種",
        "土壤",
        "病害",
    ],
    "處理法/後製": [
        "processing",
        "washed",
        "natural",
        "honey process",
        "fermentation",
        "anaerobic",
        "carbonic",
        "drying",
        "wet mill",
        "post-harvest",
        "發酵",
        "處理法",
        "後製",
        "水洗",
        "日曬",
        "蜜處理",
    ],
    "烘焙/萃取技術": [
        "roast",
        "roasting",
        "extraction",
        "espresso",
        "brew",
        "brewing",
        "grinder",
        "water",
        "sensory",
        "cupping",
        "chemistry",
        "tds",
        "electrochemical",
        "烘焙",
        "萃取",
        "濃縮",
        "感官",
    ],
    "設備/自動化": [
        "technology",
        "platform",
        "software",
        "automation",
        "sensor",
        "data",
        "ai",
        "machine learning",
        "iot",
        "drone",
        "robot",
        "app",
        "設備",
        "自動化",
        "人工智慧",
        "感測",
        "平台",
    ],
    "市場/價格": [
        "market",
        "price",
        "prices",
        "export",
        "import",
        "supply",
        "demand",
        "futures",
        "commodity",
        "ico",
        "international trade",
        "trade data",
        "consumption",
        "市場",
        "價格",
        "出口",
        "進口",
        "供應",
        "需求",
    ],
}

COFFEE_SIGNAL_TERMS = [
    "coffee",
    "coffea",
    "espresso",
    "arabica",
    "robusta",
    "canephora",
    "liberica",
    "excelsa",
    "barista",
    "roast",
    "roasting",
]

UNRELATED_RESEARCH_TERMS = [
    "brucella",
    "cattle",
    "colon cancer",
    "colorectal",
    "dental",
    "resin composite",
    "teeth",
    "tooth",
    "patients",
    "clinical trial",
]


@dataclass
class Source:
    name: str
    url: str
    kind: str = "feed"
    enabled: bool = True
    tags: list[str] = field(default_factory=list)


@dataclass
class Item:
    source: str
    title: str
    url: str
    published: str = ""
    summary: str = ""
    categories: list[str] = field(default_factory=list)
    matched_terms: list[str] = field(default_factory=list)
    score: int = 0


SEGMENT_DEFINITIONS = {
    "farm": {
        "title": "農場雷達",
        "description": "產地、農場、小農、品種、收成、供應鏈與產區組織。",
        "categories": {"農場/產地"},
        "terms": {
            "farm",
            "farms",
            "farmer",
            "farmers",
            "producer",
            "producers",
            "origin",
            "smallholder",
            "harvest",
            "arabica",
            "robusta",
            "cooperative",
        },
    },
    "processing": {
        "title": "處理法雷達",
        "description": "水洗、日曬、蜜處理、發酵、乾燥與後製技術。",
        "categories": {"處理法/後製"},
        "terms": {
            "processing",
            "washed",
            "natural",
            "honey process",
            "fermentation",
            "anaerobic",
            "carbonic",
            "drying",
            "post-harvest",
        },
    },
    "climate-tech": {
        "title": "氣候科技雷達",
        "description": "氣候韌性、土壤、病蟲害、品種育種、感測器、資料與農業工具。",
        "categories": {"種植/氣候"},
        "terms": {
            "climate",
            "climate-smart",
            "agroforestry",
            "soil",
            "drought",
            "leaf rust",
            "disease",
            "pest",
            "breeding",
            "variety",
            "resilience",
            "sustainability",
            "sensor",
            "data",
            "iot",
            "drone",
        },
    },
    "equipment": {
        "title": "設備雷達",
        "description": "烘焙機、磨豆機、義式機、萃取系統、自動化、軟體與吧台效率工具。",
        "categories": {"設備/自動化", "烘焙/萃取技術"},
        "terms": {
            "equipment",
            "machine",
            "machines",
            "espresso",
            "grinder",
            "roaster",
            "roasting",
            "extraction",
            "automation",
            "software",
            "platform",
            "technology",
            "brew",
            "brewing",
        },
    },
}


class LinkExtractor(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.links: list[tuple[str, str]] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href")
        if href:
            self._current_href = urllib.parse.urljoin(self.base_url, href)
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._current_href:
            text = clean_text(" ".join(self._current_text))
            if text:
                self.links.append((text, self._current_href))
            self._current_href = None
            self._current_text = []


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


def is_recent(value: str, days: int) -> bool:
    if days <= 0 or not value:
        return True
    parsed = parse_date(value)
    if parsed is None:
        return True
    now = dt.datetime.now(UTC)
    cutoff = now - dt.timedelta(days=days)
    if parsed > now + dt.timedelta(days=2):
        return False
    return parsed >= cutoff


def fetch_text(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def fetch_json(url: str, timeout: int = 20) -> dict[str, object]:
    return json.loads(fetch_text(url, timeout=timeout))


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":", 1)[-1]


def wanted_names(paths: Iterable[str]) -> set[str]:
    return {path.rsplit(":", 1)[-1] for path in paths}


def first_text(element: ET.Element, paths: Iterable[str]) -> str:
    wanted = wanted_names(paths)
    for child in element:
        if local_name(child.tag) in wanted:
            text = clean_text(" ".join(child.itertext()))
            if text:
                return text
    return ""


def first_link(element: ET.Element, paths: Iterable[str]) -> str:
    wanted = wanted_names(paths)
    for child in element:
        if local_name(child.tag) not in wanted:
            continue
        href = child.attrib.get("href")
        if href:
            return href.strip()
        text = clean_text(" ".join(child.itertext()))
        if text:
            return text
    return ""


def normalize_xml_entities(content: str) -> str:
    xml_entities = {"amp", "lt", "gt", "apos", "quot"}

    def replace(match: re.Match[str]) -> str:
        entity = match.group(1)
        if entity in xml_entities or entity.startswith("#"):
            return match.group(0)
        unescaped = html.unescape(match.group(0))
        if unescaped == match.group(0):
            return f"&amp;{entity};"
        return unescaped

    return re.sub(r"&([A-Za-z][A-Za-z0-9]+);", replace, content)


def parse_feed(source: Source, content: str) -> list[Item]:
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        root = ET.fromstring(normalize_xml_entities(content))

    items: list[Item] = []
    rss_items = [entry for entry in root.iter() if local_name(entry.tag) == "item"]
    atom_entries = [entry for entry in root.iter() if local_name(entry.tag) == "entry"]

    for entry in rss_items:
        title = first_text(entry, ["title"])
        url = first_link(entry, ["link", "guid"])
        published = first_text(entry, ["pubDate", "dc:date"])
        summary = first_text(entry, ["description", "content:encoded"])
        if title and url:
            items.append(Item(source.name, title, url, published, summary))

    for entry in atom_entries:
        title = first_text(entry, ["atom:title"])
        url = first_link(entry, ["atom:link"])
        published = first_text(entry, ["atom:published", "atom:updated"])
        summary = first_text(entry, ["atom:summary", "atom:content"])
        if title and url:
            items.append(Item(source.name, title, url, published, summary))

    return items


def date_parts_to_rfc3339(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    date_parts = value.get("date-parts")
    if not isinstance(date_parts, list) or not date_parts:
        return ""
    first = date_parts[0]
    if not isinstance(first, list) or not first:
        return ""
    year = int(first[0])
    month = int(first[1]) if len(first) > 1 else 1
    day = int(first[2]) if len(first) > 2 else 1
    return dt.date(year, month, day).isoformat()


def parse_crossref(source: Source, payload: dict[str, object]) -> list[Item]:
    message = payload.get("message", {})
    raw_items = message.get("items", []) if isinstance(message, dict) else []
    items: list[Item] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        titles = raw.get("title") or []
        title = clean_text(titles[0]) if isinstance(titles, list) and titles else ""
        doi = raw.get("DOI", "")
        url = raw.get("URL") or (f"https://doi.org/{doi}" if doi else "")
        published = (
            date_parts_to_rfc3339(raw.get("published-online"))
            or date_parts_to_rfc3339(raw.get("published-print"))
            or date_parts_to_rfc3339(raw.get("issued"))
            or date_parts_to_rfc3339(raw.get("created"))
        )
        journal = ""
        container = raw.get("container-title") or []
        if isinstance(container, list) and container:
            journal = clean_text(container[0])
        publisher = clean_text(str(raw.get("publisher", "")))
        abstract = clean_text(str(raw.get("abstract", "")))
        summary = " | ".join(part for part in [journal, publisher, abstract] if part)
        if title and url:
            items.append(Item(source.name, title, str(url), published, summary))
    return items


def parse_europe_pmc(source: Source, payload: dict[str, object]) -> list[Item]:
    result_list = payload.get("resultList", {})
    raw_items = result_list.get("result", []) if isinstance(result_list, dict) else []
    items: list[Item] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        title = clean_text(str(raw.get("title", "")))
        source_id = clean_text(str(raw.get("source", "")))
        record_id = clean_text(str(raw.get("id", "")))
        doi = clean_text(str(raw.get("doi", "")))
        if doi:
            url = f"https://doi.org/{doi}"
        elif source_id and record_id:
            url = f"https://europepmc.org/article/{source_id}/{record_id}"
        else:
            url = ""
        published = clean_text(
            str(raw.get("firstPublicationDate") or raw.get("firstIndexDate") or raw.get("pubYear") or "")
        )
        journal = clean_text(str(raw.get("journalTitle", "")))
        abstract = clean_text(str(raw.get("abstractText", "")))
        summary = " | ".join(part for part in [journal, abstract] if part)
        if title and url:
            items.append(Item(source.name, title, url, published, summary))
    return items


def parse_page(source: Source, content: str) -> list[Item]:
    parser = LinkExtractor(source.url)
    parser.feed(content)
    items: list[Item] = []
    seen: set[str] = set()
    for title, url in parser.links:
        normalized = normalize_url(url)
        if normalized in seen:
            continue
        seen.add(normalized)
        items.append(Item(source.name, title, url))
    return items


def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), parsed.query, "")
    )


def keyword_in_text(keyword: str, text: str) -> bool:
    keyword = keyword.lower()
    if re.fullmatch(r"[a-z0-9][a-z0-9 -]*[a-z0-9]", keyword):
        pattern = r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])"
        return re.search(pattern, text) is not None
    return keyword in text


def classify(item: Item) -> Item:
    text = f"{item.title} {item.summary}".lower()
    categories: list[str] = []
    terms: list[str] = []

    for category, keywords in CATEGORY_KEYWORDS.items():
        category_terms = [keyword for keyword in keywords if keyword_in_text(keyword, text)]
        if category_terms:
            categories.append(category)
            terms.extend(category_terms[:4])

    item.categories = categories or ["其他咖啡動態"]
    item.matched_terms = sorted(set(terms), key=str.lower)
    item.score = len(item.matched_terms) + (2 * len(categories))
    return item


def is_relevant_item(source: Source, item: Item) -> bool:
    text = f"{item.title} {item.summary}".lower()
    if source.kind in {"crossref", "europe_pmc"}:
        if not any(keyword_in_text(term, text) for term in COFFEE_SIGNAL_TERMS):
            return False
        if any(keyword_in_text(term, text) for term in UNRELATED_RESEARCH_TERMS):
            return False
    return True


def dedupe(items: Iterable[Item]) -> list[Item]:
    by_url: dict[str, Item] = {}
    for item in items:
        key = normalize_url(item.url)
        current = by_url.get(key)
        if current is None or item.score > current.score:
            by_url[key] = item
    return list(by_url.values())


def load_sources(path: Path) -> list[Source]:
    raw_sources = json.loads(path.read_text(encoding="utf-8"))
    return [Source(**raw) for raw in raw_sources if raw.get("enabled", True)]


def truncate_label(value: str, max_length: int = 26) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 1] + "…"


def progress_line(
    index: int,
    total: int,
    source_name: str,
    status: str,
    kept_items: int,
    failures: int,
) -> str:
    width = 24
    done = int((index / total) * width)
    bar = "#" * done + "-" * (width - done)
    label = truncate_label(source_name)
    return (
        f"[{bar}] {index:>2}/{total} | {label:<26} | {status:<4} "
        f"| kept={kept_items:>3} | fail={failures:>2}"
    )


def collect(sources: list[Source], days: int, minimum_score: int) -> tuple[list[Item], list[str]]:
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
            else:
                content = fetch_text(source.url)
                parsed_items = (
                    parse_page(source, content)
                    if source.kind == "page"
                    else parse_feed(source, content)
                )
        except Exception as exc:  # noqa: BLE001 - keep source failures isolated.
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

        line = progress_line(index, total_sources, source.name, status, kept_count, len(errors))
        end = "\r" if is_tty and index < total_sources else "\n"
        print(line, end=end, file=sys.stderr, flush=True)

    items = dedupe(items)
    return sorted(items, key=sort_key, reverse=True), errors


def sort_key(item: Item) -> tuple[int, str]:
    parsed = parse_date(item.published)
    date_value = parsed.isoformat() if parsed else ""
    return (item.score, date_value)


def item_to_dict(item: Item) -> dict[str, object]:
    return {
        "source": item.source,
        "title": item.title,
        "url": item.url,
        "published": item.published,
        "summary": item.summary,
        "categories": item.categories,
        "matched_terms": item.matched_terms,
        "score": item.score,
    }


def write_jsonl(items: list[Item], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for item in items:
            file.write(json.dumps(item_to_dict(item), ensure_ascii=False) + "\n")


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
        lines.extend(
            [
                f"### {index}. [{item.title}]({item.url})",
                "",
                f"- 來源：{item.source}",
                f"- 日期：{published}",
                f"- 分類：{categories}",
                f"- 命中線索：{terms}",
            ]
        )
        if summary:
            lines.append(f"- 摘要：{summary}")
        lines.append("")

    if errors:
        lines.extend(["## 抓取失敗來源", ""])
        lines.extend(f"- {error}" for error in errors)
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def item_matches_segment(item: Item, segment: dict[str, object]) -> bool:
    categories = set(item.categories)
    terms = {term.lower() for term in item.matched_terms}
    segment_categories = segment["categories"]
    segment_terms = segment["terms"]
    return bool(categories.intersection(segment_categories) or terms.intersection(segment_terms))


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
    items: list[Item],
    path: Path,
    segment: dict[str, object],
    limit: int,
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
        lines.extend(
            [
                f"### {index}. [{item.title}]({item.url})",
                "",
                f"- 來源：{item.source}",
                f"- 日期：{item.published or '未標示'}",
                f"- 分類：{categories}",
                f"- 命中線索：{terms}",
            ]
        )
        if summary:
            lines.append(f"- 摘要：{summary}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect coffee industry signals from RSS feeds and public pages."
    )
    parser.add_argument("--sources", default="sources.json", help="Path to source config JSON.")
    parser.add_argument("--days", type=int, default=45, help="Keep items from the last N days.")
    parser.add_argument("--limit", type=int, default=30, help="Maximum items in the Markdown report.")
    parser.add_argument(
        "--min-score",
        type=int,
        default=2,
        help="Minimum keyword score. Raise this to make the report stricter.",
    )
    parser.add_argument("--out", default="reports/latest.md", help="Markdown output path.")
    parser.add_argument("--jsonl", default="data/items.jsonl", help="Raw JSONL output path.")
    parser.add_argument(
        "--segment-dir",
        default="reports/segments",
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
    write_jsonl(items, Path(args.jsonl))
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
