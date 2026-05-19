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
    parse_feed, parse_page, parse_crossref, parse_europe_pmc, parse_reddit,
)
from coffee.report import write_markdown, write_segment_reports
