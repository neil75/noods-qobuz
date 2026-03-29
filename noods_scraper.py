"""
Noods Radio scraper — fetches show episodes and their tracklists.

Noods Radio uses a Kirby CMS backend at panel.noodsradio.com that exposes
a simple JSON API.

Public endpoints:
  GET https://panel.noodsradio.com/shows.json                    — 16 latest shows
  GET https://panel.noodsradio.com/shows/{slug}.json             — single show with tracklist
  GET https://panel.noodsradio.com/residents/{slug}.json         — resident info + paginated shows
  GET https://panel.noodsradio.com/residents/{slug}.json?page=N  — resident shows page N (6/page)
"""

import re
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser

import requests
from rich.console import Console

console = Console()

NOODS_PANEL = "https://panel.noodsradio.com"
NOODS_BASE = "https://noodsradio.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
}


@dataclass
class Track:
    artist: str
    title: str

    def search_query(self) -> str:
        return f"{self.artist} {self.title}"

    def __str__(self) -> str:
        return f"{self.artist} — {self.title}"


@dataclass
class Episode:
    slug: str
    name: str
    date: str = ""
    tracklist: list[Track] = field(default_factory=list)
    url: str = ""


# ---------------------------------------------------------------------------
# HTML tracklist parser
# ---------------------------------------------------------------------------

class _TextExtractor(HTMLParser):
    """Strip HTML tags, converting <br> to newlines."""

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("br",):
            self.parts.append("\n")

    def get_text(self) -> str:
        return "".join(self.parts)


def _parse_tracklist_html(html: str) -> list[Track]:
    """
    Parse the Noods Radio tracklist HTML into Track objects.

    Lines are separated by <br /> tags. Each line follows the pattern:
      Artist - Track Title
    Some lines may be empty or just whitespace — skip those.
    Split on first ' - ' only to handle titles that contain dashes.
    """
    extractor = _TextExtractor()
    extractor.feed(html)
    text = extractor.get_text()

    tracks: list[Track] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Split on first ' - ' separator
        if " - " in line:
            artist, _, title = line.partition(" - ")
            artist = artist.strip()
            title = title.strip()
            if artist and title:
                tracks.append(Track(artist=artist, title=title))
        # Lines without ' - ' are likely section headers or annotations — skip
    return tracks


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _fetch_json(url: str, params: dict = None) -> dict | list:
    resp = requests.get(url, params=params, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------

def resolve_from_url(url: str) -> tuple[str, str]:
    """
    Parse a Noods Radio URL and return (kind, slug).

    kind is 'show' or 'resident'.

    Accepted forms:
      https://noodsradio.com/shows/some-show-slug    → ('show', 'some-show-slug')
      https://noodsradio.com/residents/some-resident → ('resident', 'some-resident')
    """
    url = url.strip().rstrip("/")
    url = re.split(r"[?#]", url)[0]
    m = re.search(r"noodsradio\.com/(shows|residents)/([^/]+)", url, re.IGNORECASE)
    if not m:
        raise ValueError(
            f"Could not parse Noods Radio URL: {url!r}\n"
            "Expected: https://noodsradio.com/shows/<slug>  or  "
            "https://noodsradio.com/residents/<slug>"
        )
    kind = "show" if m.group(1) == "shows" else "resident"
    return kind, m.group(2)


# ---------------------------------------------------------------------------
# API functions
# ---------------------------------------------------------------------------

def _episode_from_data(data: dict) -> Episode:
    """Build an Episode stub from a Noods panel listing item or show object."""
    raw_id = data.get("id", "")
    slug = raw_id.split("/")[-1] if "/" in raw_id else raw_id

    tracklist_html = (data.get("tracklist") or {}).get("html", "")
    tracks = _parse_tracklist_html(tracklist_html) if tracklist_html else []

    return Episode(
        slug=slug,
        name=data.get("title", slug),
        date=data.get("date", ""),
        tracklist=tracks,
        url=f"{NOODS_BASE}/shows/{slug}" if slug else "",
    )


def get_episode(slug: str) -> Episode:
    """Fetch a single show episode by slug, including its full tracklist."""
    data = _fetch_json(f"{NOODS_PANEL}/shows/{slug}.json")
    return _episode_from_data(data)


def get_latest_shows(limit: int = 16) -> list[Episode]:
    """
    Fetch the latest shows from the Noods panel API.
    Returns Episode stubs (no tracklists) — call get_episode() to enrich.
    The shows.json endpoint returns at most 16 entries under 'latest'.
    """
    data = _fetch_json(f"{NOODS_PANEL}/shows.json")
    items = data.get("latest") or []
    return [_episode_from_data(item) for item in items[:limit]]


def get_resident_info(resident_slug: str) -> dict:
    """Return basic resident metadata (title, description, etc.)."""
    data = _fetch_json(f"{NOODS_PANEL}/residents/{resident_slug}.json")
    return {"name": data.get("title", resident_slug), "slug": resident_slug}


def get_all_resident_episodes(resident_slug: str) -> list[Episode]:
    """
    Fetch all episode stubs for a resident by paging through the API.
    Returns Episode stubs (no tracklists) — call get_episode() per item to get tracks.
    """
    episodes: list[Episode] = []
    page = 1
    while True:
        data = _fetch_json(
            f"{NOODS_PANEL}/residents/{resident_slug}.json",
            params={"page": page},
        )
        posts = data.get("posts") or []
        episodes.extend(_episode_from_data(p) for p in posts)

        pagination = data.get("pagination") or {}
        if not pagination.get("hasNextPage"):
            break
        page += 1
        time.sleep(0.3)

    return episodes
