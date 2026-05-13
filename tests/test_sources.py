import unittest
import tempfile
import json
from pathlib import Path


class SourcesTest(unittest.TestCase):
    def test_source_dataclass_defaults(self):
        from coffee.sources import Source

        source = Source(name="Test", url="https://example.com/feed")
        self.assertEqual(source.name, "Test")
        self.assertEqual(source.url, "https://example.com/feed")
        self.assertEqual(source.kind, "feed")
        self.assertTrue(source.enabled)
        self.assertEqual(source.tags, [])

    def test_source_dataclass_with_all_fields(self):
        from coffee.sources import Source

        source = Source(
            name="Test",
            url="https://example.com/api",
            kind="crossref",
            enabled=False,
            tags=["academic", "research"],
        )
        self.assertEqual(source.name, "Test")
        self.assertEqual(source.url, "https://example.com/api")
        self.assertEqual(source.kind, "crossref")
        self.assertFalse(source.enabled)
        self.assertEqual(source.tags, ["academic", "research"])

    def test_load_sources_filters_enabled(self):
        from coffee.sources import load_sources, Source

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_sources.json"
            test_data = [
                {"name": "Enabled", "url": "https://a.com"},
                {"name": "ExplicitEnabled", "url": "https://b.com", "enabled": True},
                {"name": "Disabled", "url": "https://c.com", "enabled": False},
            ]
            path.write_text(json.dumps(test_data), encoding="utf-8")

            sources = load_sources(path)

            self.assertEqual(len(sources), 2)
            names = [s.name for s in sources]
            self.assertIn("Enabled", names)
            self.assertIn("ExplicitEnabled", names)
            self.assertNotIn("Disabled", names)
            self.assertIsInstance(sources[0], Source)


if __name__ == "__main__":
    unittest.main()
