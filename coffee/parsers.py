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


def parse_reddit(source: Source, raw: str) -> list[Item]:
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        root = ET.fromstring(normalize_xml_entities(raw))
    items: list[Item] = []
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        link_el = entry.find("atom:link[@rel='alternate']", ns)
        pub_el = entry.find("atom:published", ns)
        content_el = entry.find("atom:content", ns)
        summary_el = entry.find("atom:summary", ns)

        title = clean_text(title_el.text) if title_el is not None and title_el.text else ""
        url = link_el.get("href", "") if link_el is not None else ""
        published = pub_el.text.strip() if pub_el is not None and pub_el.text else ""

        raw_text = ""
        if content_el is not None and content_el.text:
            raw_text = clean_text(content_el.text)
        elif summary_el is not None and summary_el.text:
            raw_text = clean_text(summary_el.text)

        item = Item(source.name, title, normalize_url(url), published, raw_text)
        items.append(item)
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
