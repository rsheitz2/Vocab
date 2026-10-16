from datetime import date
from unittest.mock import patch

import pytest

from vocab.db import init_db, upsert_word, seed_review_queue, get_daily_game
from vocab.display import show_blank
from vocab.fetcher import WordEntry
from vocab.game import run_daily_game, score_guess, CORRECT as C, PRESENT as P, ABSENT as A

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


def test_correct_on_sixth_try(conn):
    inputs = iter(["w1", "w2", "w3", "w4", "w5", "nexus"])
    with patch("vocab.game.Console.input", side_effect=lambda _: next(inputs)):
        result = run_daily_game(conn, _entry(), _console())
    assert result.guessed is True
    assert result.tries_used == 6


def test_exhaust_all_tries(conn):
    with patch("vocab.game.Console.input", return_value="nope"):
        result = run_daily_game(conn, _entry(), _console())
    assert result.guessed is False
    assert result.tries_used == 6


def test_case_insensitive_guess(conn):
    with patch("vocab.game.Console.input", return_value="NEXUS"):
        result = run_daily_game(conn, _entry(), _console())
    assert result.guessed is True


def test_blank_display_length():
    assert show_blank("nexus") == "_ _ _ _ _"


@pytest.mark.parametrize("revealed,expected", [
    (1, "N _ _ _ _"),
    (2, "N _ _ _ S"),
    (3, "N E _ _ S"),
    (4, "N E X _ S"),
])
def test_blank_display_reveals_letters_progressively(revealed, expected):
    assert show_blank("nexus", revealed=revealed) == expected


def test_blank_display_never_reveals_whole_word():
    assert show_blank("cat", revealed=4).count("_") == 1
    assert show_blank("go", revealed=4) == "G _"


def test_game_writes_daily_game_row(conn):
    with patch("vocab.game.Console.input", return_value="nexus"):
        run_daily_game(conn, _entry(), _console())
    row = get_daily_game(conn, date.today())
    assert row is not None
    assert row["completed"] == 1
    assert row["word"] == "nexus"


@pytest.mark.parametrize("word,definition,expected", [
    ("nexus", "A nexus is a link. Nexus can also mean a center.",
     "A _____ is a link. _____ can also mean a center."),
    ("abscond", "Someone is said to have absconded. He absconds.",
     "Someone is said to have _______ed. He _______s."),
    ("bake", "She baked bread while baking pies.", "She ____d bread while ____ing pies."),
    ("carry", "He carried it.", "He _____ed it."),
    ("plan", "They planned ahead.", "They ____ed ahead."),
    ("art", "A party of artists.", "A party of artists."),
])
def test_redact_blanks_inflections(word, definition, expected):
    from vocab.display import _redact
    assert _redact(definition, word) == expected


@pytest.mark.parametrize("guess,word,expected", [
    ("nexus", "nexus", [C, C, C, C, C]),
    ("sunex", "nexus", [P, P, P, P, P]),
    ("never", "nexus", [C, C, A, A, A]),   # second 'e' absent: the exact match claims the only one
    ("eerie", "nexus", [A, C, A, A, A]),   # exact match wins over an earlier yellow
    ("nexuses", "nexus", [C, C, C, C, C, A, A]),  # extra letters already used up
    ("nex", "nexus", [C, C, C]),
    ("sexes", "nexus", [A, C, C, A, C]),  # final s is exact, so the first s gets nothing
])
def test_score_guess(guess, word, expected):
    assert [s for _, s in score_guess(guess, word)] == expected
