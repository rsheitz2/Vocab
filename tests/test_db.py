from datetime import date, timedelta

import pytest

from vocab.db import (
    init_db,
    upsert_word,
    seed_review_queue,
    get_daily_game,
    save_daily_game,
    get_due_reviews,
    update_review,
    get_word,
    get_stats,
)
from vocab.fetcher import WordEntry


@pytest.fixture
def conn(tmp_path):
    return init_db(tmp_path / "test.db")


def _entry(word="nexus", wotd_date=None):
    return WordEntry(
        word=word,
        date=wotd_date or date(2026, 10, 12),
        definition="A connection or series of connections.",
        part_of_speech="noun",
        letter_count=len(word),
    )


def test_init_db_creates_tables(conn):
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"words", "daily_games", "review_queue"} <= tables


def test_upsert_word_idempotent(conn):
    entry = _entry()
    upsert_word(conn, entry)
    upsert_word(conn, entry)
    count = conn.execute("SELECT COUNT(*) FROM words WHERE word='nexus'").fetchone()[0]
    assert count == 1


def test_seed_review_queue_sets_interval_1(conn):
    entry = _entry()
    upsert_word(conn, entry)
    seed_review_queue(conn, entry.word, entry.date)
    row = conn.execute("SELECT * FROM review_queue WHERE word='nexus'").fetchone()
    assert row["interval_days"] == 1
    assert row["next_review"] == (entry.date + timedelta(days=1)).isoformat()


def test_seed_review_queue_idempotent(conn):
    entry = _entry()
    upsert_word(conn, entry)
    seed_review_queue(conn, entry.word, entry.date)
    seed_review_queue(conn, entry.word, entry.date)
    count = conn.execute("SELECT COUNT(*) FROM review_queue WHERE word='nexus'").fetchone()[0]
    assert count == 1


def test_get_due_reviews_filters_by_date(conn):
    today = date(2026, 10, 12)
    for word, review_date in [("nexus", today), ("vapid", today + timedelta(days=5))]:
        e = _entry(word=word, wotd_date=today)
        upsert_word(conn, e)
        conn.execute(
            "INSERT OR IGNORE INTO review_queue (word, next_review, interval_days) VALUES (?, ?, 1)",
            (word, review_date.isoformat()),
        )
    conn.commit()
    due = get_due_reviews(conn, today)
    assert len(due) == 1
    assert due[0]["word"] == "nexus"


def test_update_review_correct_doubles(conn):
    entry = _entry()
    upsert_word(conn, entry)
    conn.execute(
        "INSERT INTO review_queue (word, next_review, interval_days) VALUES ('nexus', '2026-10-13', 4)"
    )
    conn.commit()
    update_review(conn, "nexus", correct=True)
    row = conn.execute("SELECT interval_days FROM review_queue WHERE word='nexus'").fetchone()
    assert row["interval_days"] == 8


def test_update_review_correct_caps_at_60(conn):
    entry = _entry()
    upsert_word(conn, entry)
    conn.execute(
        "INSERT INTO review_queue (word, next_review, interval_days) VALUES ('nexus', '2026-10-13', 32)"
    )
    conn.commit()
    update_review(conn, "nexus", correct=True)
    row = conn.execute("SELECT interval_days FROM review_queue WHERE word='nexus'").fetchone()
    assert row["interval_days"] == 60


def test_update_review_wrong_halves(conn):
    entry = _entry()
    upsert_word(conn, entry)
    conn.execute(
        "INSERT INTO review_queue (word, next_review, interval_days) VALUES ('nexus', '2026-10-13', 8)"
    )
    conn.commit()
    update_review(conn, "nexus", correct=False)
    row = conn.execute("SELECT interval_days FROM review_queue WHERE word='nexus'").fetchone()
    assert row["interval_days"] == 4


def test_update_review_wrong_min_1(conn):
    entry = _entry()
    upsert_word(conn, entry)
    conn.execute(
        "INSERT INTO review_queue (word, next_review, interval_days) VALUES ('nexus', '2026-10-13', 1)"
    )
    conn.commit()
    update_review(conn, "nexus", correct=False)
    row = conn.execute("SELECT interval_days FROM review_queue WHERE word='nexus'").fetchone()
    assert row["interval_days"] == 1


def test_save_daily_game_marks_completed(conn):
    entry = _entry()
    upsert_word(conn, entry)
    save_daily_game(conn, date(2026, 10, 12), "nexus", True, 2)
    row = get_daily_game(conn, date(2026, 10, 12))
    assert row is not None
    assert row["completed"] == 1
    assert row["guessed"] == 1
    assert row["tries_used"] == 2


def test_get_daily_game_returns_none_for_missing_date(conn):
    row = get_daily_game(conn, date(2026, 1, 1))
    assert row is None


def test_get_stats_returns_correct_counts(conn):
    entry = _entry()
    upsert_word(conn, entry)
    save_daily_game(conn, date.today(), "nexus", True, 1)
    stats = get_stats(conn)
    assert stats["total_words"] == 1
    assert stats["daily_streak"] == 1
