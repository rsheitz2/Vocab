import sqlite3
from dataclasses import dataclass

from rich.console import Console

from vocab import db, display


@dataclass
class ReviewResult:
    total: int
    correct: int
    wrong: int


def run_review_session(
    conn: sqlite3.Connection, due_words: list, console: Console
) -> ReviewResult:
    correct_count = 0
    wrong_count = 0

    for word_row in due_words:
        word = word_row["word"]
        display.show_review_puzzle(word_row, console)
        try:
            guess = console.input("[bold]Your guess:[/bold] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Review interrupted.[/dim]")
            break

        correct = guess == word
        display.show_review_outcome(word, correct, console)
        db.update_review(conn, word, correct)
        console.print()

        if correct:
            correct_count += 1
        else:
            wrong_count += 1

    return ReviewResult(
        total=correct_count + wrong_count,
        correct=correct_count,
        wrong=wrong_count,
    )
