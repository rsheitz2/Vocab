from datetime import date
from unittest.mock import patch, MagicMock

import pytest

from vocab.fetcher import fetch_wotd, FetchError, _parse_entry, WordEntry
import xml.etree.ElementTree as ET

_SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>nexus</title>
      <pubDate>Mon, 12 Oct 2026 00:00:01 -0400</pubDate>
      <description><![CDATA[
        <p>Merriam-Webster's Word of the Day for October 12, 2026 is:</p>
        <p><strong>nexus</strong> &#8226; \\NEK-sus\\ &#8226; <em>noun</em><br>
        : a connection or link between things</p>
        <p>A nexus is a central connection that links related things together.</p>
        <p>// "The city serves as a nexus for trade."</p>
      ]]></description>
    </item>
  </channel>
</rss>"""


def _make_mock_response(xml_content):
    mock = MagicMock()
    mock.content = xml_content.encode("utf-8")
    mock.raise_for_status = MagicMock()
    return mock


def test_parse_entry_extracts_word():
    root = ET.fromstring(_SAMPLE_RSS)
    item = root.find("channel/item")
    entry = _parse_entry(item)
    assert entry.word == "nexus"


def test_parse_entry_extracts_pos():
    root = ET.fromstring(_SAMPLE_RSS)
    item = root.find("channel/item")
    entry = _parse_entry(item)
    assert entry.part_of_speech == "noun"


def test_parse_entry_extracts_definition():
    root = ET.fromstring(_SAMPLE_RSS)
    item = root.find("channel/item")
    entry = _parse_entry(item)
    assert "nexus" in entry.definition.lower()


def test_parse_entry_sets_letter_count():
    root = ET.fromstring(_SAMPLE_RSS)
    item = root.find("channel/item")
    entry = _parse_entry(item)
    assert entry.letter_count == 5


def test_parse_entry_sets_date():
    root = ET.fromstring(_SAMPLE_RSS)
    item = root.find("channel/item")
    entry = _parse_entry(item)
    assert entry.date == date(2026, 10, 12)


def test_fetch_raises_on_network_error():
    import requests as req
    with patch("vocab.fetcher.requests.get", side_effect=req.RequestException("timeout")):
        with pytest.raises(FetchError, match="Network error"):
            fetch_wotd()


def test_fetch_raises_on_too_few_paragraphs():
    bad_rss = """<?xml version="1.0"?>
<rss><channel><item>
  <title>nexus</title>
  <pubDate>Mon, 12 Oct 2026 00:00:01 -0400</pubDate>
  <description><![CDATA[<p>Only one paragraph.</p>]]></description>
</item></channel></rss>"""
    with patch("vocab.fetcher.requests.get", return_value=_make_mock_response(bad_rss)):
        with pytest.raises(FetchError):
            fetch_wotd()


def test_fetch_returns_word_entry():
    with patch("vocab.fetcher.requests.get", return_value=_make_mock_response(_SAMPLE_RSS)):
        entry = fetch_wotd()
    assert isinstance(entry, WordEntry)
    assert entry.word == "nexus"
    assert entry.letter_count == 5


@pytest.mark.network
def test_fetch_live():
    entry = fetch_wotd()
    assert entry.word
    assert entry.letter_count == len(entry.word)
    assert entry.definition
    assert entry.part_of_speech in {
        "noun", "verb", "adjective", "adverb", "pronoun",
        "preposition", "conjunction", "interjection", "unknown",
    }
