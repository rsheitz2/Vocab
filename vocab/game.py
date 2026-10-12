import sqlite3
from dataclasses import dataclass
from datetime import date

from rich.console import Console

from vocab import audio, db, display
from vocab.fetcher import WordEntry


@dataclass
class GameResult:
    word: str
    guessed: bool
    tries_used: int


def run_daily_game(conn: sqlite3.Connection, entry: WordEntry, console: Console) -> GameResult:
    for attempt in range(1, 4):
        display.show_puzzle(entry, hint_level=attempt, console=console)
        try:
            while True:
                guess = console.input("[bold]Your guess[/bold] [dim]('p' to pronounce)[/dim]: ").strip().lower()
                if guess == "p":
                    audio.play_word(entry.word, console)
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

        if attempt < 3:
            console.print("[red]Not quite — try again.[/red]\n")

    display.show_wrong(entry.word, console)
    result = GameResult(word=entry.word, guessed=False, tries_used=3)
    db.save_daily_game(conn, date.today(), entry.word, False, 3)
    db.update_review(conn, entry.word, correct=False)
    return result
