from datetime import date, timedelta
from unittest.mock import patch

import pytest

from rich.console import Console

from vocab.db import init_db, upsert_word, seed_review_queue, get_due_reviews, update_review
from vocab.fetcher import WordEntry
from vocab.review import run_review_session


@pytest.fixture
def conn(tmp_path):
    c = init_db(tmp_path / "test.db")
    today = date.today()
    for word in ["nexus", "vapid", "lucid"]:
        e = WordEntry(word, today, f"Definition of {word}.", "adjective", len(word))
        upsert_word(c, e)
        c.execute(
            "INSERT OR IGNORE INTO review_queue (word, next_review, interval_days) VALUES (?, ?, ?)",
            (word, today.isoformat(), 4),
        )
    c.commit()
    return c


def _console():
    return Console(highlight=False)


def test_correct_review_updates_interval(conn):
    conn.execute(
        "UPDATE review_queue SET interval_days = 4 WHERE word = 'nexus'"
    )
    conn.commit()
    update_review(conn, "nexus", correct=True)
    row = conn.execute("SELECT interval_days FROM review_queue WHERE word='nexus'").fetchone()
    assert row["interval_days"] == 8


def test_wrong_review_updates_interval(conn):
    conn.execute(
        "UPDATE review_queue SET interval_days = 4 WHERE word = 'nexus'"
    )
    conn.commit()
    update_review(conn, "nexus", correct=False)
    row = conn.execute("SELECT interval_days FROM review_queue WHERE word='nexus'").fetchone()
    assert row["interval_days"] == 2


def test_review_session_returns_counts(conn):
    due = get_due_reviews(conn, date.today())
    # nexus=correct, vapid=correct, lucid=wrong
    words_in_order = [r["word"] for r in due]
    answers = {w: w for w in words_in_order}  # correct guess = the word itself
    answers[words_in_order[2]] = "wrong_answer"

    inputs = iter([answers[w] for w in words_in_order])
    with patch("vocab.review.Console.input", side_effect=lambda _: next(inputs)):
        result = run_review_session(conn, due, _console())

    assert result.total == 3
    assert result.correct == 2
    assert result.wrong == 1


def test_no_reviews_due_returns_empty(conn):
    future = date.today() + timedelta(days=5)
    due = get_due_reviews(conn, future - timedelta(days=10))
    assert due == []
