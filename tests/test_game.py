from datetime import date
from unittest.mock import patch

import pytest

from vocab.db import init_db, upsert_word, seed_review_queue, get_daily_game
from vocab.display import show_blank
from vocab.fetcher import WordEntry
from vocab.game import run_daily_game

from rich.console import Console


@pytest.fixture
def conn(tmp_path):
    c = init_db(tmp_path / "test.db")
    entry = WordEntry("nexus", date(2026, 10, 12), "A central link.", "noun", 5)
    upsert_word(c, entry)
    seed_review_queue(c, "nexus", date(2026, 10, 12))
    return c


def _entry():
    return WordEntry("nexus", date(2026, 10, 12), "A central link.", "noun", 5)


def _console():
    return Console(highlight=False)


def test_correct_on_first_try(conn):
    with patch("vocab.game.Console.input", return_value="nexus"):
        result = run_daily_game(conn, _entry(), _console())
    assert result.guessed is True
    assert result.tries_used == 1


def test_correct_on_third_try(conn):
    inputs = iter(["wrong", "also wrong", "nexus"])
    with patch("vocab.game.Console.input", side_effect=lambda _: next(inputs)):
        result = run_daily_game(conn, _entry(), _console())
    assert result.guessed is True
    assert result.tries_used == 3


def test_exhaust_all_tries(conn):
    with patch("vocab.game.Console.input", return_value="nope"):
        result = run_daily_game(conn, _entry(), _console())
    assert result.guessed is False
    assert result.tries_used == 3


def test_case_insensitive_guess(conn):
    with patch("vocab.game.Console.input", return_value="NEXUS"):
        result = run_daily_game(conn, _entry(), _console())
    assert result.guessed is True


def test_blank_display_length():
    assert show_blank("nexus") == "_ _ _ _ _"


def test_blank_display_with_first_letter():
    result = show_blank("nexus", first_letter=True)
    assert result.startswith("N")
    assert result.count("_") == 4


def test_game_writes_daily_game_row(conn):
    with patch("vocab.game.Console.input", return_value="nexus"):
        run_daily_game(conn, _entry(), _console())
    row = get_daily_game(conn, date.today())
    assert row is not None
    assert row["completed"] == 1
    assert row["word"] == "nexus"
