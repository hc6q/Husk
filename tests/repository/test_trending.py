"""Offline tests for the GitHub Trending README widget."""
import datetime as dt
import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("widget", ROOT / "scripts/update_trending.py")
widget = importlib.util.module_from_spec(spec)
spec.loader.exec_module(widget)


def html_fixture():
    return "<html><body>" + "".join(
        '<article class="Box-row">'
        '<a href="/login?return_to=x">Login</a>'
        f'<h2 class="h3 lh-condensed"><a href="/owner{n}/project{n}">repo</a></h2>'
        f'<p class="col-9 color-fg-muted">Description &amp; details {n}</p>'
        '<span itemprop="programmingLanguage">Python</span>'
        '<span>Built by 123 stars today</span>'
        '</article>' for n in range(6)
    ) + "</body></html>"


class TrendingTests(unittest.TestCase):
    def test_parses_real_repo_in_heading(self):
        rows = widget.parse(html_fixture())
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]["name"], "owner0/project0")
        self.assertEqual(rows[0]["stars"], 123)
        self.assertEqual(rows[0]["description"], "Description & details 0")

    def test_rejects_empty_or_changed_markup(self):
        with self.assertRaises(ValueError):
            widget.parse("<html>Not Trending</html>")

    def test_svg_is_xml_and_escaped(self):
        rows = widget.parse(html_fixture())
        rows[0]["name"] = "owner/<repo&>"
        svg = widget.render(rows, dt.date(2026, 10, 7))
        ET.fromstring(svg)
        self.assertIn("owner/&lt;repo&amp;&gt;", svg)
        self.assertIn(">+123</text>", svg)
        self.assertIn("2026-10-07", svg)


if __name__ == "__main__":
    unittest.main()
