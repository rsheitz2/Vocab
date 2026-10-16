import sqlite3
from dataclasses import dataclass
from datetime import date

from rich.console import Console

from vocab import audio, db, display, literature
from vocab.fetcher import WordEntry


MAX_TRIES = 6

CORRECT, PRESENT, ABSENT = "correct", "present", "absent"


@dataclass
class GameResult:
    word: str
    guessed: bool
    tries_used: int


def score_guess(guess: str, word: str) -> list[tuple[str, str]]:
    """Wordle-style scoring: each guess letter is CORRECT (right spot), PRESENT
    (elsewhere in the word) or ABSENT. Repeated letters only count as often as
    they appear in the word, with exact matches claimed first."""
    statuses = [ABSENT] * len(guess)
    remaining: dict[str, int] = {}
    for i, c in enumerate(word):
        if i < len(guess) and guess[i] == c:
            statuses[i] = CORRECT
        else:
            remaining[c] = remaining.get(c, 0) + 1
    for i, c in enumerate(guess):
        if statuses[i] != CORRECT and remaining.get(c, 0) > 0:
            statuses[i] = PRESENT
            remaining[c] -= 1
    return list(zip(guess, statuses))


def run_daily_game(conn: sqlite3.Connection, entry: WordEntry, console: Console) -> GameResult:
    scored_guesses: list[list[tuple[str, str]]] = []
    for attempt in range(1, MAX_TRIES + 1):
        display.show_puzzle(entry, hint_level=attempt, console=console, guesses=scored_guesses)
        try:
            while True:
                guess = console.input(
                    "[bold]Your guess[/bold] [dim]('p' pronounce · 'e' examples)[/dim]: "
                ).strip().lower()
                if guess == "p":
                    audio.play_word(entry.word, console)
                elif guess == "e":
                    lit, rate_limited = literature.get_or_fetch(conn, entry.word)
                    display.show_examples(entry, lit, console, rate_limited=rate_limited)
                else:
                    break
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Game interrupted. Re-run to continue.[/dim]")
            raise

        if guess == entry.word:
            display.show_correct(entry.word, attempt, console)
            result = GameResult(word=entry.word, guessed=True, tries_used=attempt)
            db.save_daily_game(conn, date.today(), entry.word, True, attempt)
            db.update_review(conn, entry.word, correct=True)
            return result

        scored_guesses.append(score_guess(guess, entry.word))
        if attempt < MAX_TRIES:
            console.print("[red]Not quite — try again.[/red]\n")

    display.show_wrong(entry.word, console)
    result = GameResult(word=entry.word, guessed=False, tries_used=MAX_TRIES)
    db.save_daily_game(conn, date.today(), entry.word, False, MAX_TRIES)
    db.update_review(conn, entry.word, correct=False)
    return result
