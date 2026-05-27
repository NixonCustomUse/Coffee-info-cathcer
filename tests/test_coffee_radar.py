import datetime as dt
import unittest
from pathlib import Path

from coffee.sources import Source
from coffee.classify import (
    classify,
    item_matches_segment,
    is_recent,
    is_relevant_item,
    SEGMENT_DEFINITIONS,
)
from coffee.parsers import parse_crossref, parse_europe_pmc, parse_feed, parse_reddit
from coffee_radar import _fallback_summary_zh


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


SAMPLE_REDDIT_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/">
  <title>coffee</title>
  <entry>
    <title>Best pourover technique for light roasts?</title>
    <link href="https://www.reddit.com/r/coffee/comments/abc123/" rel="alternate"/>
    <published>2026-05-19T14:30:00+00:00</published>
    <updated>2026-05-19T15:00:00+00:00</updated>
    <author><name>/u/coffeelover</name></author>
    <summary type="html">&lt;p&gt;I've been experimenting with light roasts and found that a slower pour works better.&lt;/p&gt;</summary>
    <media:thumbnail xmlns:media="http://search.yahoo.com/mrss/" url="https://example.com/thumb.jpg"/>
  </entry>
  <entry>
    <title>New espresso machine recommendations under $500</title>
    <link href="https://www.reddit.com/r/espresso/comments/def456/" rel="alternate"/>
    <published>2026-05-18T09:15:00+00:00</published>
    <updated>2026-05-18T10:00:00+00:00</updated>
    <author><name>/u/espresso_fan</name></author>
    <content type="html">&lt;p&gt;Looking for a budget-friendly espresso machine.&lt;/p&gt;</content>
  </entry>
</feed>"""


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
        summary = _fallback_summary_zh(item)
        self.assertIn("這篇來自 Example", summary)
        self.assertIn("農場/產地", summary)



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

    def test_reddit_parser(self):
        source = Source(name="r/coffee", url="https://www.reddit.com/r/coffee/.rss", kind="reddit")
        items = parse_reddit(source, SAMPLE_REDDIT_RSS)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].title, "Best pourover technique for light roasts?")
        self.assertEqual(items[0].url, "https://www.reddit.com/r/coffee/comments/abc123")
        self.assertEqual(items[0].published, "2026-05-19T14:30:00+00:00")
        self.assertIn("slower pour", items[0].summary)
        self.assertIn("budget-friendly", items[1].summary)
        self.assertEqual(items[1].title, "New espresso machine recommendations under $500")


if __name__ == "__main__":
    unittest.main()
