import unittest
import tempfile
from pathlib import Path

from coffee_ai import fallback_summary_zh, generate_weekly_article
from coffee_notion_sync import SyncState
from coffee_radar import (
    Source,
    classify,
    item_matches_segment,
    parse_crossref,
    parse_europe_pmc,
    parse_feed,
    is_recent,
    is_relevant_item,
    SEGMENT_DEFINITIONS,
)
from coffee_weekly import select_recent_items


SAMPLE_FEED = """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>Coffee Test Feed</title>
    <item>
      <title>New climate-smart platform helps coffee farms choose resilient varieties</title>
      <link>https://example.com/coffee-climate-platform</link>
      <pubDate>Thu, 07 May 2026 10:00:00 +0000</pubDate>
      <description>Farmers use data, breeding insights, and replanting plans.</description>
    </item>
  </channel>
</rss>
"""


class CoffeeRadarTest(unittest.TestCase):
    def test_parse_feed_and_classify(self):
        source = Source(name="Example", url="https://example.com/feed")
        items = parse_feed(source, SAMPLE_FEED)
        self.assertEqual(len(items), 1)

        item = classify(items[0])
        self.assertIn("農場/產地", item.categories)
        self.assertIn("種植/氣候", item.categories)
        self.assertIn("設備/自動化", item.categories)
        self.assertGreaterEqual(item.score, 6)

    def test_fallback_chinese_summary(self):
        item = {
            "title": "New robusta trial improves yields",
            "source": "Example",
            "categories": ["農場/產地", "種植/氣候"],
            "summary": "Farmers tested robusta varieties and saw better yields.",
        }
        summary = fallback_summary_zh(item)
        self.assertIn("這篇來自 Example", summary)
        self.assertIn("農場/產地", summary)

    def test_select_recent_items(self):
        items = [
            {"title": "new", "published": "Thu, 07 May 2026 10:00:00 +0000", "score": 3},
            {"title": "old", "published": "Thu, 01 Jan 2026 10:00:00 +0000", "score": 9},
        ]
        selected = select_recent_items(items, days=7)
        self.assertEqual(selected[0]["title"], "new")

    def test_weekly_article_fallback_sections(self):
        article = generate_weekly_article(
            [
                {
                    "title": "Climate-smart coffee farming",
                    "url": "https://example.com/a",
                    "categories": ["種植/氣候"],
                    "score": 5,
                    "zh_summary": "氣候韌性種植工具值得追蹤。",
                }
            ],
            title="Coffee Radar 週報：2026-W19",
            use_ai=False,
        )
        self.assertIn("新研究與產地訊號", article)
        self.assertIn("下週追蹤問題", article)

    def test_sync_state_dedupes_urls(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = SyncState(Path(tmpdir) / "state.sqlite")
            self.assertFalse(state.has_url("https://example.com/a/"))
            state.mark_url("https://example.com/a/", "page-id", "Title")
            self.assertTrue(state.has_url("https://example.com/a"))

    def test_crossref_parser(self):
        source = Source(name="Crossref", url="https://api.crossref.org/works", kind="crossref")
        payload = {
            "message": {
                "items": [
                    {
                        "title": ["Coffee fermentation improves sensory quality"],
                        "URL": "https://doi.org/10.123/example",
                        "published-online": {"date-parts": [[2026, 5, 1]]},
                        "container-title": ["Coffee Journal"],
                        "abstract": "A study about coffee processing.",
                    }
                ]
            }
        }
        items = parse_crossref(source, payload)
        self.assertEqual(items[0].published, "2026-05-01")
        self.assertIn("Coffee Journal", items[0].summary)

    def test_europe_pmc_parser(self):
        source = Source(name="Europe PMC", url="https://example.com", kind="europe_pmc")
        payload = {
            "resultList": {
                "result": [
                    {
                        "title": "Climate-smart coffee replanting",
                        "source": "MED",
                        "id": "123",
                        "doi": "",
                        "firstPublicationDate": "2026-05-03",
                        "journalTitle": "Agronomy",
                        "abstractText": "Coffee climate resilience research.",
                    }
                ]
            }
        }
        items = parse_europe_pmc(source, payload)
        self.assertEqual(items[0].url, "https://europepmc.org/article/MED/123")
        self.assertIn("Agronomy", items[0].summary)

    def test_segment_matching(self):
        source = Source(name="Example", url="https://example.com/feed")
        item = classify(
            parse_feed(
                source,
                """<?xml version="1.0"?>
                <rss version="2.0"><channel><item>
                <title>Anaerobic fermentation for coffee processing</title>
                <link>https://example.com/processing</link>
                <description>New post-harvest drying process.</description>
                </item></channel></rss>""",
            )[0]
        )
        self.assertTrue(item_matches_segment(item, SEGMENT_DEFINITIONS["processing"]))

    def test_academic_filter_rejects_unrelated_health_item(self):
        source = Source(name="Europe PMC", url="https://example.com", kind="europe_pmc")
        item = parse_europe_pmc(
            source,
            {
                "resultList": {
                    "result": [
                        {
                            "title": "Dental resin composites after immersion in coffee",
                            "source": "MED",
                            "id": "123",
                            "abstractText": "A clinical study in patients about teeth staining.",
                        }
                    ]
                }
            },
        )[0]
        self.assertFalse(is_relevant_item(source, item))

    def test_future_dates_are_not_recent(self):
        self.assertFalse(is_recent("2099-01-01", days=120))


if __name__ == "__main__":
    unittest.main()
