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
  You have [bold]3 tries[/bold] to guess the word, with hints revealed after each wrong guess:

    Try 1 — definition + blank letters  (e.g. [cyan]_ _ _ _ _[/cyan])
    Try 2 — + part of speech            (e.g. [yellow]noun[/yellow])
    Try 3 — + first letter              (e.g. [cyan]N _ _ _ _[/cyan])

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
  [dim]./vocab.sh[/dim]           Show this help"""


def show_help() -> None:
    console.print(Panel(_HELP, title="[bold]Vocab Help[/bold]", border_style="blue", padding=(1, 2)))


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] not in ("start", "history"):
        show_help()
        return

    conn = db.init_db()

    if args[0] == "history":
        browse_words(conn, console)
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
    due = db.get_due_reviews(conn, today)
    if due:
        console.print(f"[bold]Review time:[/bold] {len(due)} word(s) due today.\n")
        result = run_review_session(conn, due, console)
        console.print(
            f"[bold]Review complete:[/bold] {result.correct}/{result.total} correct\n"
        )
    else:
        console.print("[dim]No reviews due today.[/dim]\n")

    display.show_stats(db.get_stats(conn), console)


if __name__ == "__main__":
    main()
