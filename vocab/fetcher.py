import email.utils
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date

import requests
from bs4 import BeautifulSoup

RSS_URL = "https://www.merriam-webster.com/wotd/feed/rss2"


class FetchError(Exception):
    pass


@dataclass
class WordEntry:
    word: str
    date: date
    definition: str
    part_of_speech: str
    letter_count: int
    pronunciation: str = ""
    examples: str = ""
    did_you_know: str = ""


def _parse_entry(item: ET.Element) -> WordEntry:
    title = item.findtext("title", "").strip().lower()
    if not title:
        raise FetchError("RSS item missing title")

    pub_date_str = item.findtext("pubDate", "")
    try:
        wotd_date = email.utils.parsedate_to_datetime(pub_date_str).date()
    except Exception as exc:
        raise FetchError(f"Could not parse pubDate '{pub_date_str}'") from exc

    description = item.findtext("description", "")
    soup = BeautifulSoup(description, "html.parser")
    paragraphs = soup.find_all("p")

    if len(paragraphs) < 3:
        raise FetchError(
            f"Unexpected RSS description structure: only {len(paragraphs)} <p> tags found"
        )

    em_tag = paragraphs[1].find("em")
    part_of_speech = em_tag.get_text().strip() if em_tag else "unknown"

    header_parts = paragraphs[1].get_text().split("•")
    pronunciation = header_parts[1].strip() if len(header_parts) >= 3 else ""

    definition = paragraphs[2].get_text().strip()
    if not definition:
        raise FetchError("Could not extract definition from RSS description")

    examples = []
    did_you_know = ""
    for p in paragraphs[3:]:
        text = p.get_text().strip()
        if text.startswith("//"):
            examples.append(text[2:].strip())
        elif text.startswith(('"', '“')) and len(text) > 20 and " — " in text:
            # Real-world quote with citation: "text..." — Author, Publication, Date
            examples.append(text)
        elif text.lower().startswith("did you know"):
            did_you_know = text.split("\n", 1)[-1].strip()

    return WordEntry(
        word=title,
        date=wotd_date,
        definition=definition,
        part_of_speech=part_of_speech,
        letter_count=len(title),
        pronunciation=pronunciation,
        examples="\n".join(examples),
        did_you_know=did_you_know,
    )


def fetch_wotd(conn=None) -> WordEntry:
    try:
        response = requests.get(
            RSS_URL,
            headers={"User-Agent": "Vocab/1.0"},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise FetchError(f"Network error fetching M-W RSS: {exc}") from exc

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as exc:
        raise FetchError(f"Failed to parse RSS XML: {exc}") from exc

    channel = root.find("channel")
    if channel is None:
        raise FetchError("RSS feed missing <channel> element")

    item = channel.find("item")
    if item is None:
        raise FetchError("RSS feed has no <item> elements")

    entry = _parse_entry(item)

    if conn is not None:
        from vocab.db import upsert_word, seed_review_queue
        upsert_word(conn, entry)
        seed_review_queue(conn, entry.word, entry.date)

    return entry
