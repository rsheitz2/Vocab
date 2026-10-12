import sqlite3

from prompt_toolkit import Application
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import ConditionalContainer, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel

_STYLE = Style.from_dict({
    "header":     "bg:#003566 #ffffff bold",
    "footer":     "bg:#001d3d #aaaaaa",
    "selected":   "bg:#0077b6 #ffffff bold",
    "correct":    "#52b788",
    "wrong":      "#e63946",
    "neutral":    "#888888",
    "word":       "#90e0ef bold",
    "date":       "#888888",
    "definition": "#cccccc",
    "search":     "bg:#001d3d #ffffff",
    "search-bar": "bg:#001d3d #ffd60a bold",
})

_HEADER = (
    "  Vocab History"
    "   [j/k] navigate  [/] search  [Enter] select  [Esc/q] quit  "
)


def _load_words(conn: sqlite3.Connection) -> list:
    return conn.execute(
        "SELECT w.word, w.date, w.definition, w.letter_count, "
        "w.pronunciation, w.part_of_speech, w.examples, w.did_you_know, "
        "w.literary_examples, "
        "dg.guessed, dg.tries_used, "
        "rq.next_review, rq.interval_days, rq.review_count "
        "FROM words w "
        "LEFT JOIN daily_games dg ON w.word = dg.word "
        "LEFT JOIN review_queue rq ON w.word = rq.word "
        "ORDER BY w.date DESC"
    ).fetchall()


def _matches(row, query: str) -> bool:
    q = query.lower()
    return q in row["word"] or q in row["definition"].lower()


def browse_words(conn: sqlite3.Connection, console: Console) -> None:
    all_words = _load_words(conn)
    if not all_words:
        console.print("[dim]No words in history yet.[/dim]")
        return

    state = {"cursor": 0, "query": "", "search": False, "selected": None}

    def filtered() -> list:
        if not state["query"]:
            return list(all_words)
        return [r for r in all_words if _matches(r, state["query"])]

    def _list_content() -> StyleAndTextTuples:
        rows = filtered()
        if state["cursor"] >= len(rows):
            state["cursor"] = max(0, len(rows) - 1)

        out: StyleAndTextTuples = []
        for i, row in enumerate(rows):
            sel = i == state["cursor"]
            guessed = row["guessed"]
            if guessed is None:
                badge = ("class:neutral", " ·  ")
            elif guessed:
                badge = ("class:correct", " ✓  ")
            else:
                badge = ("class:wrong", " ✗  ")

            word = row["word"].ljust(18)
            date = (row["date"] or "          ")[:10]
            defn = row["definition"]
            preview = (defn[:52] + "…") if len(defn) > 52 else defn

            if sel:
                line = f" ▶  {word}  {date}  "
                out += [("class:selected", line), ("class:selected", badge[1]),
                        ("class:selected", f"  {preview}\n")]
            else:
                out += [("", f"    {word}  {date}  "), badge,
                        ("class:definition", f"  {preview}\n")]

        if not rows:
            out.append(("class:neutral", "  No matches.\n"))
        return out

    def _footer_content() -> StyleAndTextTuples:
        if state["search"]:
            return [("class:search-bar", f"  /{state['query']}▌")]
        total = len(all_words)
        shown = len(filtered())
        label = f"  {shown}/{total} words"
        if state["query"]:
            label += f'  (filter: "{state["query"]}"  Esc to clear)'
        return [("class:footer", label)]

    kb = KeyBindings()
    normal = ~Condition(lambda: state["search"])
    search = Condition(lambda: state["search"])

    @kb.add("j", filter=normal)
    @kb.add("down", filter=normal)
    def _down(event):
        rows = filtered()
        state["cursor"] = min(state["cursor"] + 1, max(0, len(rows) - 1))

    @kb.add("k", filter=normal)
    @kb.add("up", filter=normal)
    def _up(event):
        state["cursor"] = max(state["cursor"] - 1, 0)

    @kb.add("g", filter=normal)
    def _top(event):
        state["cursor"] = 0

    @kb.add("G", filter=normal)
    def _bottom(event):
        rows = filtered()
        state["cursor"] = max(0, len(rows) - 1)

    @kb.add("/", filter=normal)
    def _enter_search(event):
        state["search"] = True

    @kb.add("<any>", filter=search)
    def _type(event):
        key = event.key_sequence[0].key
        if len(key) == 1 and key.isprintable():
            state["query"] += key
            state["cursor"] = 0

    @kb.add("backspace", filter=search)
    def _backspace(event):
        state["query"] = state["query"][:-1]
        state["cursor"] = 0

    @kb.add("enter", filter=search)
    def _commit_search(event):
        state["search"] = False

    @kb.add("escape")
    def _escape(event):
        if state["search"]:
            state["search"] = False
            state["query"] = ""
            state["cursor"] = 0
        else:
            event.app.exit()

    @kb.add("q", filter=normal)
    def _quit(event):
        event.app.exit()

    @kb.add("enter", filter=normal)
    def _select(event):
        rows = filtered()
        if rows:
            state["selected"] = rows[state["cursor"]]
            event.app.exit()

    layout = Layout(
        HSplit([
            Window(FormattedTextControl(lambda: [("class:header", _HEADER)]), height=1),
            Window(FormattedTextControl(_list_content, focusable=False)),
            Window(FormattedTextControl(_footer_content), height=1),
        ])
    )

    app = Application(layout=layout, key_bindings=kb, style=_STYLE, full_screen=True, mouse_support=True)
    app.run()

    if state["selected"] is not None:
        _show_detail(state["selected"], conn, console)


def _show_detail(row, conn: sqlite3.Connection, console: Console) -> None:
    from vocab import display, literature

    console.print()

    # Show definition panel
    word = row["word"]
    pronunciation = row["pronunciation"] or ""
    definition = row["definition"]
    pos = row["part_of_speech"] or ""

    title_parts = [f"[bold cyan]{word.upper()}[/bold cyan]"]
    if pos:
        title_parts.append(f"[dim]{pos}[/dim]")
    if pronunciation:
        title_parts.append(f"[dim]{pronunciation}[/dim]")

    console.print(Panel(
        definition,
        title="  ".join(title_parts),
        border_style="cyan",
    ))

    # Show examples + literary quotes
    lit, rate_limited = literature.get_or_fetch(conn, word)
    display.show_examples(row, lit, console, rate_limited=rate_limited)

    # Review stats
    guessed = row["guessed"]
    if guessed is None:
        result_str = "[dim]not yet played[/dim]"
    elif guessed:
        tries = row["tries_used"]
        result_str = f"[green]Correct[/green] in {tries} {'try' if tries == 1 else 'tries'}"
    else:
        result_str = "[red]Failed[/red]"

    next_review = row["next_review"] or "—"
    interval = row["interval_days"] or "—"
    reviews = row["review_count"] or 0

    stats_line = (
        f"{result_str}  ·  "
        f"Next review: [cyan]{next_review}[/cyan]  ·  "
        f"Interval: [cyan]{interval}d[/cyan]  ·  "
        f"Reviews: [cyan]{reviews}[/cyan]"
    )
    console.print(Panel(stats_line, title="[dim]Stats[/dim]", border_style="dim"))
