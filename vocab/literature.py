import json
import os
import re
import sqlite3

import requests

BOOKS_API = "https://www.googleapis.com/books/v1/volumes"

# Set GOOGLE_BOOKS_API_KEY in your environment for reliable access.
# Get a free key at: https://console.cloud.google.com/apis/library/books.googleapis.com
_API_KEY = os.environ.get("GOOGLE_BOOKS_API_KEY", "")

# Sentinel stored in DB to indicate "already fetched, no results / rate-limited"
_NO_RESULTS = "[]"
# Empty string means "never attempted" — will retry on next e press
_NOT_FETCHED = ""


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return (
        text.replace("&amp;", "&")
            .replace("&quot;", '"')
            .replace("&#39;", "'")
            .replace("…", "...")
            .strip()
    )


def fetch_literary_examples(word: str, max_results: int = 3) -> list[dict] | None:
    """Fetch book quotes from Google Books API.

    Returns a list of result dicts, or None on rate-limit/network failure
    (caller should not cache None so it can retry later).
    """
    params = {
        "q": f'"{word}"',
        "langRestrict": "en",
        "maxResults": 10,
        "printType": "books",
        "orderBy": "relevance",
    }
    if _API_KEY:
        params["key"] = _API_KEY

    try:
        resp = requests.get(
            BOOKS_API,
            params=params,
            headers={"User-Agent": "Vocab/1.0"},
            timeout=10,
        )
        if resp.status_code == 429:
            return None  # rate-limited — don't cache, retry next time
        resp.raise_for_status()
    except requests.RequestException:
        return None

    results = []
    for item in resp.json().get("items", []):
        info = item.get("volumeInfo", {})
        snippet = _clean(item.get("searchInfo", {}).get("textSnippet", ""))
        if not snippet:
            continue
        authors = info.get("authors", [])
        results.append({
            "snippet": snippet,
            "title": info.get("title", "Unknown"),
            "author": ", ".join(authors[:2]) if authors else "Unknown",
            "year": info.get("publishedDate", "")[:4],
        })
        if len(results) >= max_results:
            break

    return results


def get_or_fetch(conn: sqlite3.Connection, word: str) -> tuple[list[dict], bool]:
    """Return (examples, rate_limited).

    rate_limited=True means the API was unavailable — caller can show a hint.
    """
    row = conn.execute(
        "SELECT literary_examples FROM words WHERE word = ?", (word,)
    ).fetchone()

    if row is None:
        return [], False

    cached = row["literary_examples"]
    if cached:
        return json.loads(cached), False

    examples = fetch_literary_examples(word)
    if examples is None:
        return [], True  # rate-limited — don't cache, try again next time

    conn.execute(
        "UPDATE words SET literary_examples = ? WHERE word = ?",
        (json.dumps(examples), word),
    )
    conn.commit()
    return examples, False
