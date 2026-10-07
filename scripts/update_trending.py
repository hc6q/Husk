#!/usr/bin/env python3
"""Refresh the GitHub Trending widget used in the README.

Public GitHub Trending, not a ranking of Rottweiler's own activity.
The SVG is generated without additional Python dependencies.
"""

from __future__ import annotations

import argparse
import datetime as dt
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.request import Request, urlopen

URL = "https://github.com/trending?since=daily"
OUTPUT = Path(__file__).resolve().parents[1] / "docs/assets/github-trending.svg"
REPO_PATH = re.compile(r"^/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/?$")
TODAY = re.compile(r"([\d,]+)\s+stars?\s+today\b", re.IGNORECASE)


class TrendingParser(HTMLParser):
    """Only accept repository links in Trending article headings."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.repos = []
        self.current = None
        self.h2 = False
        self.description = False
        self.language = False
        self.text = []
        self.description_text = []
        self.language_text = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = (a.get("class") or "").split()
        if tag == "article" and "Box-row" in classes:
            self.current = {}
            self.text = []
            self.description_text = []
            self.language_text = []
            return
        if self.current is None:
            return
        if tag == "h2":
            self.h2 = True
        elif tag == "a" and self.h2:
            m = REPO_PATH.fullmatch(a.get("href") or "")
            if m and "name" not in self.current:
                self.current["name"] = m.group(1) + "/" + m.group(2)
        elif tag == "p" and "col-9" in classes:
            self.description = True
        elif a.get("itemprop") == "programmingLanguage":
            self.language = True

    def handle_data(self, text):
        if self.current is not None:
            self.text.append(text)
            if self.description:
                self.description_text.append(text)
            if self.language:
                self.language_text.append(text)

    def handle_endtag(self, tag):
        if self.current is None:
            return
        if tag == "h2":
            self.h2 = False
        elif tag == "p":
            self.description = False
        elif tag == "span" and self.language:
            self.language = False
        elif tag == "article":
            combined = " ".join(" ".join(self.text).split())
            match = TODAY.search(combined)
            if "name" in self.current:
                self.current["stars"] = int(match.group(1).replace(",", "")) if match else None
                self.current["description"] = " ".join(" ".join(self.description_text).split())
                self.current["language"] = " ".join(" ".join(self.language_text).split())
                self.repos.append(self.current)
            self.current = None
            self.h2 = self.description = self.language = False


def parse(html):
    parser = TrendingParser()
    parser.feed(html)
    repos = parser.repos
    if len(repos) < 5:
        raise ValueError(f"GitHub Trending returned only {len(repos)} repositories")
    if any(r["stars"] is None for r in repos[:5]):
        raise ValueError("GitHub Trending daily star count markup has changed")
    return repos[:5]


def fetch():
    request = Request(URL, headers={
        "Accept": "text/html",
        "User-Agent": "Mozilla/5.0 (compatible; RottweilerTrending/1.0; +https://github.com/hc6q/Rottweiler)",
    })
    with urlopen(request, timeout=30) as response:
        markup = response.read().decode("utf-8", errors="replace")
    return parse(markup)


def trim(value, n):
    return value if len(value) <= n else value[:n - 1].rstrip() + "…"


def render(repos, date):
    items = []
    for idx, repo in enumerate(repos[:5], 1):
        y = 144 + (idx - 1) * 72
        name = escape(trim(repo["name"], 41))
        desc = escape(trim(repo.get("description") or "No description", 75))
        lang = escape(trim(repo.get("language") or "Unspecified", 20))
        stars = f'+{repo["stars"]:,}' if repo["stars"] is not None else "—"
        items.append(f"""  <g>
    <text x="49" y="{y + 19}" class="rank">{idx:02d}</text>
    <text x="106" y="{y + 13}" class="repo">{name}</text>
    <text x="106" y="{y + 38}" class="desc">{desc}</text>
    <text x="959" y="{y + 15}" text-anchor="end" class="lang">{lang}</text>
    <path d="M8 0 L10.5 5.5 L16.5 6.2 L12 10.3 L13.2 16.2 L8 13.1 L2.8 16.2 L4 10.3 L-0.5 6.2 L5.5 5.5 Z" transform="translate(1017 {y + 2})" fill="#dfaf91"/>
    <text x="1129" y="{y + 15}" text-anchor="end" class="stars">{stars}</text>
    <path d="M49 {y + 51} H1130" stroke="#24262b" stroke-width="1"/>
  </g>""")
    content = "\n".join(items)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="559" viewBox="0 0 1180 559" role="img" aria-labelledby="title description">
  <title id="title">GitHub Trending — top five repositories today</title>
  <desc id="description">Updated {date.isoformat()} UTC from the public GitHub Trending daily list. Names, descriptions, languages and stars gained today.</desc>
  <style>
    .overline {{ fill:#a8abb5; font:600 13px -apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif; letter-spacing:2.5px; }}
    .heading {{ fill:#f7f7f8; font:700 34px -apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif; }}
    .muted {{ fill:#858892; font:400 14px -apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif; }}
    .repo {{ fill:#f2f3f4; font:600 19px -apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif; }}
    .desc {{ fill:#858892; font:400 14px -apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif; }}
    .rank {{ fill:#6f727d; font:600 21px ui-monospace,SFMono-Regular,Consolas,monospace; }}
    .lang {{ fill:#969ba3; font:500 13px -apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif; }}
    .stars {{ fill:#dfaf91; font:600 17px ui-monospace,SFMono-Regular,Consolas,monospace; }}
  </style>
  <rect x="1" y="1" width="1178" height="557" rx="18" fill="#0f1013" stroke="#2c2e34" stroke-width="2"/>
  <path d="M49 44 H76" stroke="#db9f8c" stroke-width="3" stroke-linecap="round"/>
  <text x="91" y="49" class="overline">DISCOVER / GITHUB</text>
  <text x="49" y="98" class="heading">Trending today</text>
  <text x="1130" y="94" class="muted" text-anchor="end">Global · {date.isoformat()} UTC</text>
  <path d="M49 120 H1130" stroke="#33353b" stroke-width="1"/>
{content}
  <text x="49" y="532" class="muted">Source: github.com/trending · Refreshed daily by GitHub Actions</text>
  <text x="1130" y="532" class="muted" text-anchor="end">Stars gained today</text>
</svg>
"""


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--output", type=Path, default=OUTPUT)
    options = args.parse_args()
    result = render(fetch(), dt.datetime.now(dt.timezone.utc).date())
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(result, encoding="utf-8")
    print(f"Updated {options.output}")


if __name__ == "__main__":
    main()
