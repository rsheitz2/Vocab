import sys
from datetime import date

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from vocab import db, display
from vocab.fetcher import fetch_wotd, FetchError
from vocab.game import run_daily_game
from vocab.history import browse_words
from vocab.review import run_review_session

console = Console()

_HELP = """[bold blue]Vocab[/bold blue] — a daily word-guessing game powered by Merriam-Webster.

[bold]How to play[/bold]
  Each day a new Word of the Day is fetched from Merriam-Webster.
  You are shown the [cyan]definition[/cyan] and the [cyan]number of letters[/cyan].
  You have [bold]6 tries[/bold] to guess the word, with hints revealed after each wrong guess:

    Try 1 — definition + blank letters  (e.g. [cyan]_ _ _ _ _[/cyan])
    Try 2 — + part of speech            (e.g. [yellow]noun[/yellow])
    Try 3 — + first letter              (e.g. [cyan]N _ _ _ _[/cyan])
    Try 4 — + last letter               (e.g. [cyan]N _ _ _ S[/cyan])
    Try 5 — + second letter             (e.g. [cyan]N E _ _ S[/cyan])
    Try 6 — + middle letter             (e.g. [cyan]N E X _ S[/cyan])

  Each wrong guess is shown with colored letters:
    [bold black on green] A [/bold black on green]  right letter, right spot
    [bold black on yellow] A [/bold black on yellow]  in the word, wrong spot
    [bold white on grey35] A [/bold white on grey35]  not in the word

  At any guess prompt: [bold]p[/bold] = hear pronunciation · [bold]e[/bold] = examples, phonetic guide & etymology

[bold]Review mode[/bold]
  After the daily game, past words due for review appear automatically.
  You get [bold]1 try[/bold] per review word (definition + letter count only).
  [green]Correct[/green] → word comes back later (interval doubles, max 60 days).
  [red]Wrong[/red]   → word comes back sooner (interval halves, min 1 day).

[bold]Word history[/bold]
  Browse every past word in a searchable list with its pronunciation.
  Press [bold]p[/bold] to hear a word; select it to see its full definition,
  examples, and review stats.

[bold]Usage[/bold]
  [dim]./vocab.sh start[/dim]     Play today's game
  [dim]./vocab.sh history[/dim]   Browse past words (vi-style)
  [dim]./vocab.sh review[/dim]    Review words due today (skips the daily game)
  [dim]./vocab.sh review --all[/dim]  Review every saved word, due or not
  [dim]./vocab.sh[/dim]           Show this help"""


def show_help() -> None:
    console.print(Panel(_HELP, title="[bold]Vocab Help[/bold]", border_style="blue", padding=(1, 2)))


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] not in ("start", "history", "review"):
        show_help()
        return

    conn = db.init_db()

    if args[0] == "history":
        browse_words(conn, console)
        return

    if args[0] == "review":
        run_reviews(conn, all_words="--all" in args[1:])
        return

    try:
        entry = fetch_wotd(conn)
    except FetchError as exc:
        today_game = db.get_daily_game(conn, date.today())
        if today_game and today_game["completed"]:
            console.print(f"[yellow]Could not fetch today's word ({exc}). Showing reviews.[/yellow]\n")
            entry = None
        else:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            return

    today = date.today()

    if entry is not None:
        today_game = db.get_daily_game(conn, today)
        if today_game and today_game["completed"]:
            display.show_already_played(today_game, console)
        else:
            console.print(f"\n[bold blue]Vocab[/bold blue] · Word of the Day for {today}\n")
            run_daily_game(conn, entry, console)

    console.print()
    run_reviews(conn)


def run_reviews(conn, all_words: bool = False) -> None:
    if all_words:
        words = db.get_all_reviews(conn)
        label, empty = "saved", "[dim]No saved words yet.[/dim]\n"
    else:
        words = db.get_due_reviews(conn, date.today())
        label, empty = "due today", "[dim]No reviews due today.[/dim]\n"

    if words:
        console.print(f"[bold]Review time:[/bold] {len(words)} word(s) {label}.\n")
        result = run_review_session(conn, words, console)
        console.print(
            f"[bold]Review complete:[/bold] {result.correct}/{result.total} correct\n"
        )
    else:
        console.print(empty)

    display.show_stats(db.get_stats(conn), console)


if __name__ == "__main__":
    main()
