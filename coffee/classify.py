from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from typing import Iterable

from coffee.util import clean_text, normalize_url, parse_date, UTC


CATEGORY_KEYWORDS = {
    "農場/產地": [
        "farm", "farms", "farmer", "farmers", "producer", "producers",
        "origin", "estate", "cooperative", "smallholder", "finca",
        "plantation", "harvest", "terroir", "traceability", "single origin",
        "arabica", "robusta", "geisha", "gesha", "農場", "產地", "莊園", "小農",
    ],
    "種植/氣候": [
        "climate", "agroforestry", "shade", "irrigation", "soil",
        "drought", "leaf rust", "disease", "pest", "replanting",
        "seedling", "breeding", "variety", "resilience", "sustainability",
        "climate-smart", "氣候", "育種", "品種", "土壤", "病害",
    ],
    "處理法/後製": [
        "processing", "washed", "natural", "honey process", "fermentation",
        "anaerobic", "carbonic", "drying", "wet mill", "post-harvest",
        "發酵", "處理法", "後製", "水洗", "日曬", "蜜處理",
    ],
    "烘焙/萃取技術": [
        "roast", "roasting", "extraction", "espresso", "brew", "brewing",
        "grinder", "water", "sensory", "cupping", "chemistry", "tds",
        "electrochemical", "烘焙", "萃取", "濃縮", "感官",
    ],
    "設備/自動化": [
        "technology", "platform", "software", "automation", "sensor",
        "data", "ai", "machine learning", "iot", "drone", "robot", "app",
        "設備", "自動化", "人工智慧", "感測", "平台",
    ],
    "市場/價格": [
        "market", "price", "prices", "export", "import", "supply",
        "demand", "futures", "commodity", "ico", "international trade",
        "trade data", "consumption", "市場", "價格", "出口", "進口",
        "供應", "需求",
    ],
}

COFFEE_SIGNAL_TERMS = [
    "coffee", "coffea", "espresso", "arabica", "robusta", "canephora",
    "liberica", "excelsa", "barista", "roast", "roasting",
]

UNRELATED_RESEARCH_TERMS = [
    "brucella", "cattle", "colon cancer", "colorectal", "dental",
    "resin composite", "teeth", "tooth", "patients", "clinical trial",
]


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
            "farm", "farms", "farmer", "farmers", "producer", "producers",
            "origin", "smallholder", "harvest", "arabica", "robusta", "cooperative",
        },
    },
    "processing": {
        "title": "處理法雷達",
        "description": "水洗、日曬、蜜處理、發酵、乾燥與後製技術。",
        "categories": {"處理法/後製"},
        "terms": {
            "processing", "washed", "natural", "honey process", "fermentation",
            "anaerobic", "carbonic", "drying", "post-harvest",
        },
    },
    "climate-tech": {
        "title": "氣候科技雷達",
        "description": "氣候韌性、土壤、病蟲害、品種育種、感測器、資料與農業工具。",
        "categories": {"種植/氣候"},
        "terms": {
            "climate", "climate-smart", "agroforestry", "soil", "drought",
            "leaf rust", "disease", "pest", "breeding", "variety",
            "resilience", "sustainability", "sensor", "data", "iot", "drone",
        },
    },
    "equipment": {
        "title": "設備雷達",
        "description": "烘焙機、磨豆機、義式機、萃取系統、自動化、軟體與吧台效率工具。",
        "categories": {"設備/自動化", "烘焙/萃取技術"},
        "terms": {
            "equipment", "machine", "machines", "espresso", "grinder",
            "roaster", "roasting", "extraction", "automation", "software",
            "platform", "technology", "brew", "brewing",
        },
    },
}


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
        category_terms = [kw for kw in keywords if keyword_in_text(kw, text)]
        if category_terms:
            categories.append(category)
            terms.extend(category_terms[:4])

    item.categories = categories or ["其他咖啡動態"]
    item.matched_terms = sorted(set(terms), key=str.lower)
    item.score = len(item.matched_terms) + (2 * len(categories))
    return item


def is_relevant_item(source, item: Item) -> bool:
    text = f"{item.title} {item.summary}".lower()
    if source.kind in {"crossref", "europe_pmc"}:
        if not any(keyword_in_text(term, text) for term in COFFEE_SIGNAL_TERMS):
            return False
        if any(keyword_in_text(term, text) for term in UNRELATED_RESEARCH_TERMS):
            return False
    return True


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


def dedupe(items: Iterable[Item]) -> list[Item]:
    by_url: dict[str, Item] = {}
    for item in items:
        key = normalize_url(item.url)
        current = by_url.get(key)
        if current is None or item.score > current.score:
            by_url[key] = item
    return list(by_url.values())


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


def item_matches_segment(item: Item, segment: dict[str, object]) -> bool:
    categories = set(item.categories)
    terms = {term.lower() for term in item.matched_terms}
    segment_categories = segment["categories"]
    segment_terms = segment["terms"]
    return bool(categories.intersection(segment_categories) or terms.intersection(segment_terms))
