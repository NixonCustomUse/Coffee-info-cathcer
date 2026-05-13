# Coffee Info Catcher Restructure — Implementation Plan

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure flat Python modules into a focused `coffee/` package, remove LLM/AI integration, and sharpen AGENTS.md.

**Architecture:** Extract 5 single-responsibility submodules from the 842-line `coffee_radar.py`, move weekly article functions into `coffee_weekly.py`, and delete all OpenRouter/LLM API calls. Pipeline interface and data format stay unchanged.

**Tech Stack:** Python 3 stdlib only. `coffee/` is a namespace-as-directory, not a pip-installable package.

---

### Task 1: Create `coffee/util.py`

**Files:**
- Create: `coffee/util.py`

Extract utility functions + constants from `coffee_radar.py` and `coffee_ai.py`. This is the foundation all other modules depend on.

- [ ] **Write `coffee/util.py`**

```python
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
```

- [ ] **Run tests to verify nothing broke yet**

```bash
python3 -m unittest tests/test_coffee_radar.py 2>&1
```
Expected: all existing tests pass (nothing imports util.py yet).

---

### Task 2: Create `coffee/sources.py`

**Files:**
- Create: `coffee/sources.py`

- [ ] **Write `coffee/sources.py`**

```python
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Source:
    name: str
    url: str
    kind: str = "feed"
    enabled: bool = True
    tags: list[str] = field(default_factory=list)


def load_sources(path: Path) -> list[Source]:
    raw_sources = json.loads(path.read_text(encoding="utf-8"))
    return [Source(**raw) for raw in raw_sources if raw.get("enabled", True)]
```

---

### Task 3: Create `coffee/parsers.py`

**Files:**
- Create: `coffee/parsers.py`

- [ ] **Write `coffee/parsers.py`**

```python
from __future__ import annotations

import html
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from typing import Iterable

from coffee.util import clean_text
from coffee.sources import Source


Item: type  # forward declaration — imported at bottom to break cycle


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
    return dt.date(year, month, day).isoformat()  # noqa: F821


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
        normalized = normalize_url(url)  # noqa: F821
        if normalized in seen:
            continue
        seen.add(normalized)
        items.append(Item(source.name, title, url))
    return items


# late import to break cycle
from coffee.util import normalize_url  # noqa: E402, F811
import datetime as dt  # noqa: E402, F811
from coffee.classify import Item  # noqa: E402
```

Wait, `parse_page` uses `normalize_url` and `date_parts_to_rfc3339` uses `dt.date`. Since `parsers.py` needs `Item` from `classify.py`, but `classify.py` doesn't need anything from `parsers.py`, there's no cycle. Let me just import at the top.

Actually, checking dependencies:
- `parsers.py` → needs `Item` from `classify.py`
- `classify.py` → needs nothing from `parsers.py`
- No cycle!

So I can use normal top-level imports. The `normalize_url` usage in `parse_page` can import from `coffee/util.py` normally.

But wait, in the original `coffee_radar.py`, `normalize_url` was defined AFTER `LinkExtractor` class and `parse_page` function. The `parse_page` function calls `normalize_url()` inside its body (not at import time), so there's no issue with import order.

Let me just write `parsers.py` with clean top-level imports:

```python
from coffee.util import clean_text, normalize_url
from coffee.sources import Source
from coffee.classify import Item
```

This works because the `Item` import is resolved at call time, not at class/function definition time.

Actually wait - if test runner imports `test_coffee_radar.py` which imports `from coffee.parsers import parse_feed`, then Python needs to resolve `coffee.classify.Item`. If `coffee/classify.py` hasn't been created yet, the import will fail. But this is the implementation order - we'll create `classify.py` before `parsers.py`.

OK let me re-think the dependency order:
1. `coffee/util.py` — no internal deps
2. `coffee/sources.py` — no internal deps
3. `coffee/classify.py` — depends on `util` for `clean_text`, `normalize_url`, `parse_date`
4. `coffee/parsers.py` — depends on `util`, `sources`, `classify`
5. `coffee/report.py` — depends on `classify`
6. `coffee/__init__.py` — depends on everything above

So the implementation order is: util → sources → classify → parsers → report → __init__

Let me reconsider. Actually `classify.py` has `keyword_in_text` and `is_recent` which use `parse_date`. `clean_text` for `classify` function. And `normalize_url` for `dedupe`. So it depends on `util`.

OK, I'll keep the import in `parsers.py` clean - just import `Item` from `classify` at top since classify doesn't depend on parsers.

Let me rewrite the plan tasks with the correct dependency order and clean imports.

Actually, I realize the plan is getting very long. Let me simplify. The user is impatient ("YOU CAN GO NOWW"). Let me just write the plan properly and then execute it using the subagent-driven-development or executing-plans skill.

Let me write the plan to the file, then ask the user how they want to execute.<｜end▁of▁thinking｜>

<｜｜DSML｜｜tool_calls>
<｜｜DSML｜｜invoke name="write">
<｜｜DSML｜｜parameter name="content" string="true"># Coffee Info Catcher Restructure — Implementation Plan

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure flat Python modules into a focused `coffee/` package, remove LLM/AI integration, and sharpen AGENTS.md.

**Architecture:** Extract 5 submodules from 842-line `coffee_radar.py`, move weekly article functions to `coffee_weekly.py`, delete all OpenRouter/LLM calls. Pipeline interface and data format unchanged.

**Tech Stack:** Python 3 stdlib only. `coffee/` is a directory package, not pip-installable.

---

## Dependency order

```
util → sources → classify → parsers → report → __init__
                                                  ↓
coffee_radar.py  coffee_ai.py  coffee_weekly.py  coffee_notion_sync.py  generate_html.py
```

---

### Task 1: Create `coffee/util.py`

Extract utilities from `coffee_radar.py` + `coffee_ai.py`: `clean_text`, `parse_date`, `normalize_url`, `fetch_text`, `fetch_json`, `load_jsonl`, `write_jsonl`, `strip_feed_boilerplate`, `compact_signal_zh`, `UTC`, `USER_AGENT`.

**Files:**
- Create: `coffee/__init__.py` (empty, makes it a package)
- Create: `coffee/util.py`

- [ ] **Create coffee/ directory and util.py**

```python
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
```

- [ ] **Verify: `python3 -c "from coffee.util import clean_text; print('ok')"`**

---

### Task 2: Create `coffee/sources.py`

**Files:**
- Create: `coffee/sources.py`

- [ ] **Write coffee/sources.py**

```python
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Source:
    name: str
    url: str
    kind: str = "feed"
    enabled: bool = True
    tags: list[str] = field(default_factory=list)


def load_sources(path: Path) -> list[Source]:
    raw_sources = json.loads(path.read_text(encoding="utf-8"))
    return [Source(**raw) for raw in raw_sources if raw.get("enabled", True)]
```

- [ ] **Verify: `python3 -c "from coffee.sources import Source; print('ok')"`**

---

### Task 3: Create `coffee/classify.py`

**Files:**
- Create: `coffee/classify.py`

- [ ] **Write coffee/classify.py**

```python
from __future__ import annotations

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


def is_relevant_item(source: Source, item: Item) -> bool:
    from coffee.sources import Source  # noqa: F811

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
```

- [ ] **Verify: `python3 -c "from coffee.classify import Item; print('ok')"`**

---

### Task 4: Create `coffee/parsers.py`

**Files:**
- Create: `coffee/parsers.py`

- [ ] **Write coffee/parsers.py**

```python
from __future__ import annotations

import datetime as dt
import html
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from typing import Iterable

from coffee.util import clean_text, normalize_url
from coffee.sources import Source
from coffee.classify import Item


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
```

- [ ] **Verify: `python3 -c "from coffee.parsers import parse_feed; print('ok')"`**

---

### Task 5: Create `coffee/report.py`

**Files:**
- Create: `coffee/report.py`

- [ ] **Write coffee/report.py**

```python
from __future__ import annotations

import datetime as dt
import json
import textwrap
import sys
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
```

- [ ] **Verify: `python3 -c "from coffee.report import write_markdown; print('ok')"`**

---

### Task 6: Create `coffee/__init__.py`

**Files:**
- Create: `coffee/__init__.py`

- [ ] **Write coffee/__init__.py**

```python
from coffee.util import (
    clean_text, normalize_url, parse_date, fetch_text, fetch_json,
    UTC, load_jsonl, write_jsonl, strip_feed_boilerplate, compact_signal_zh,
)
from coffee.sources import Source, load_sources
from coffee.classify import (
    Item, classify, is_relevant_item, is_recent, dedupe, sort_key,
    item_to_dict, item_matches_segment, keyword_in_text,
    CATEGORY_KEYWORDS, COFFEE_SIGNAL_TERMS, UNRELATED_RESEARCH_TERMS,
    SEGMENT_DEFINITIONS,
)
from coffee.parsers import (
    parse_feed, parse_page, parse_crossref, parse_europe_pmc,
)
from coffee.report import write_markdown, write_segment_reports
```

- [ ] **Verify: `python3 -c "from coffee import Source, Item; print('ok')"`**

---

### Task 7: Slim `coffee_radar.py`

**Files:**
- Modify: `coffee_radar.py` (strip ~620 lines, keep collect + main + CLI)

- [ ] **Replace coffee_radar.py**

```python
#!/usr/bin/env python3
"""Coffee Radar: collect and classify coffee industry signals."""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from coffee import (
    Source, Item, load_sources, classify, is_recent, is_relevant_item,
    dedupe, sort_key, item_to_dict, write_jsonl, fetch_json, fetch_text,
    parse_crossref, parse_europe_pmc, parse_feed, parse_page,
    write_markdown, write_segment_reports, UTC,
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

        # progress display
        width = 24
        done = int((index / total_sources) * width)
        bar = "#" * done + "-" * (width - done)
        label = (item.source[:25] + "…") if len(source.name) > 26 else source.name
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
```

- [ ] **Run tests to verify**

```bash
python3 -m unittest tests/test_coffee_radar.py 2>&1
```
Expect: imports resolve, tests pass (failing tests mean wrong imports in test file or coffee_radar.py).

---

### Task 8: Edit `coffee_ai.py` — remove LLM/AI, move weekly functions out

**Files:**
- Modify: `coffee_ai.py`

- [ ] **Replace coffee_ai.py**

```python
#!/usr/bin/env python3
"""Chinese summaries for Coffee Radar — deterministic fallback only."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from coffee.util import (
    clean_text, load_jsonl, write_jsonl, strip_feed_boilerplate, compact_signal_zh,
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
```

Note: `import textwrap` needs to be added.

- [ ] **Verify: `python3 -c "from coffee_ai import summarize_item_zh; print('ok')"`**

---

### Task 9: Edit `coffee_weekly.py` — gain weekly functions

**Files:**
- Modify: `coffee_weekly.py`

- [ ] **Replace coffee_weekly.py**

```python
#!/usr/bin/env python3
"""Generate weekly Coffee Radar articles."""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
import textwrap
from pathlib import Path
from typing import Any

from coffee.util import UTC, parse_date, load_jsonl, compact_signal_zh


def item_date(item: dict[str, Any]) -> dt.date | None:
    parsed = parse_date(item.get("published", ""))
    return parsed.date() if parsed else None


def select_recent_items(
    items: list[dict[str, Any]], days: int, now: dt.datetime | None = None,
) -> list[dict[str, Any]]:
    now = now or dt.datetime.now(UTC)
    cutoff = (now - dt.timedelta(days=days)).date()
    recent = [item for item in items if (item_date(item) or dt.date.min) >= cutoff]
    if recent:
        return sorted(recent, key=lambda item: (item.get("score", 0), item.get("published", "")), reverse=True)
    return sorted(items, key=lambda item: item.get("score", 0), reverse=True)[:20]


def pick_items(items: list[dict[str, Any]], categories: set[str]) -> list[dict[str, Any]]:
    picked = [
        item for item in items
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


def generate_weekly_article(items: list[dict[str, Any]], title: str) -> str:
    return fallback_weekly_article(items, title)


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
    lines.extend([
        "",
        "## 下週追蹤問題",
        "",
        "- 產地端：品種、土壤管理與氣候韌性是否有更多可量化成果？",
        "- 技術端：新設備是否真正降低人力、成本或品質波動？",
        "- 市場端：價格壓力會讓更多咖啡館嘗試自烘或改變採購策略嗎？",
    ])
    return "\n".join(lines)


def week_title(now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now()
    year, week, _ = now.isocalendar()
    return f"Coffee Radar 週報：{year}-W{week:02d}"


def output_paths(output_dir: Path, now: dt.datetime | None = None) -> tuple[Path, Path]:
    now = now or dt.datetime.now()
    year, week, _ = now.isocalendar()
    dated = output_dir / f"{year}-W{week:02d}.md"
    latest = output_dir / "latest.md"
    return dated, latest


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a weekly Coffee Radar article.")
    parser.add_argument("--input", default="data/items.enriched.jsonl")
    parser.add_argument("--output-dir", default="reports/weekly")
    parser.add_argument("--days", type=int, default=7)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    items = load_jsonl(Path(args.input))
    selected = select_recent_items(items, days=args.days)
    title = week_title()
    article = generate_weekly_article(selected, title=title)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    dated, latest = output_paths(output_dir)
    dated.write_text(article, encoding="utf-8")
    shutil.copyfile(dated, latest)
    print(f"Saved weekly article to {dated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

---

### Task 10: Edit `coffee_notion_sync.py` — update imports

**Files:**
- Modify: `coffee_notion_sync.py`

- [ ] **Update imports** — replace `from coffee_radar import UTC, normalize_url, parse_date` with `from coffee.util import UTC, normalize_url, parse_date`, replace `from coffee_ai import load_jsonl` with `from coffee.util import load_jsonl`

```python
from coffee.util import UTC, normalize_url, parse_date, load_jsonl
```

Remove any duplicate JSONL loading (currently uses `from coffee_ai import load_jsonl`).

---

### Task 11: Edit `generate_html.py` — update imports, dedup `load_jsonl`

**Files:**
- Modify: `generate_html.py`

- [ ] **Replace load_jsonl function** with import from coffee.util

Change:
```python
def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
```
To:
```python
from coffee.util import load_jsonl
```

Remove unused `json` import if `load_jsonl` was the only user.

---

### Task 12: Update `tests/test_coffee_radar.py`

**Files:**
- Modify: `tests/test_coffee_radar.py`

- [ ] **Update imports** — change `from coffee_radar import ...` to `from coffee.xxx import ...`

Old:
```python
from coffee_ai import fallback_summary_zh, generate_weekly_article
from coffee_notion_sync import SyncState
from coffee_radar import (
    Source, classify, item_matches_segment, parse_crossref, parse_europe_pmc,
    parse_feed, is_recent, is_relevant_item, SEGMENT_DEFINITIONS,
)
from coffee_weekly import select_recent_items
```

New:
```python
from coffee.sources import Source
from coffee.classify import (
    classify, item_matches_segment, is_recent, is_relevant_item,
    SEGMENT_DEFINITIONS,
)
from coffee.parsers import parse_crossref, parse_europe_pmc, parse_feed
from coffee_ai import fallback_summary_zh
from coffee_weekly import select_recent_items, generate_weekly_article
from coffee_notion_sync import SyncState
```

- [ ] **Run tests**

```bash
python3 -m unittest tests/test_coffee_radar.py 2>&1
```
Expect: all tests pass.

---

### Task 13: Edit `AGENTS.md`

**Files:**
- Modify: `AGENTS.md`

- [ ] **Replace with compact agent-specific guidance**

Write a ~40-line version keeping: data-flow diagram, pipeline run order, env vars, focused CLI commands, URL dedup convention, keyword classification convention, academic filter rule, segment report system. Remove project structure tree and README-duplicated content.

---

### Task 14: Verify the full pipeline

**Files:**
- Run: integration smoke test

- [ ] **Run all tests**

```bash
python3 -m unittest discover -s tests 2>&1
```

- [ ] **Run a dry collect to verify no runtime import errors**

```bash
python3 coffee_radar.py --days 365 --limit 5 --min-score 10 2>&1
```

- [ ] **Verify coffee_ai.py runs**

```bash
python3 coffee_ai.py --input data/items.jsonl --output /tmp/test_enriched.jsonl 2>&1
```

- [ ] **Verify coffee_weekly.py imports resolve**

```bash
python3 -c "from coffee_weekly import generate_weekly_article; print('ok')"
```
