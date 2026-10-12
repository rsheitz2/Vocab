import re

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


def _redact(definition: str, word: str) -> str:
    blank = "_" * len(word)
    return re.sub(rf"\b{re.escape(word)}\b", blank, definition, flags=re.IGNORECASE)


def show_blank(word: str, first_letter: bool = False) -> str:
    if first_letter and word:
        return word[0].upper() + " " + " ".join("_" * (len(word) - 1))
    return " ".join("_" * len(word))


def show_puzzle(entry, hint_level: int, console: Console) -> None:
    lines = [Text(_redact(entry.definition, entry.word), style="white")]

    if hint_level >= 2:
        lines.append(Text(""))
        lines.append(Text(f"Part of speech: {entry.part_of_speech}", style="yellow"))

    lines.append(Text(""))
    blank = show_blank(entry.word, first_letter=(hint_level >= 3))
    hint_line = Text(f"Letters: {entry.letter_count}  →  {blank}", style="cyan bold")
    if getattr(entry, "pronunciation", ""):
        hint_line.append(f"   {entry.pronunciation}", style="dim")
    lines.append(hint_line)

    body = Text("\n").join(lines)
    title = f"[bold blue]Vocab[/bold blue] · Guess #{hint_level}"
    console.print(Panel(body, title=title, border_style="blue"))


def show_correct(word: str, tries: int, console: Console) -> None:
    s = "try" if tries == 1 else "tries"
    console.print(
        Panel(
            Text(f'Correct! The word was "{word.upper()}"  ({tries} {s})', style="bold green"),
            border_style="green",
        )
    )


def show_wrong(word: str, console: Console) -> None:
    console.print(
        Panel(
            Text(f'The word was "{word.upper()}"', style="bold red"),
            title="[red]Better luck tomorrow[/red]",
            border_style="red",
        )
    )


def show_review_puzzle(word_row, console: Console) -> None:
    blank = show_blank(word_row["word"])
    body = Text(_redact(word_row["definition"], word_row["word"]) + "\n\n", style="white")
    body.append(f"Letters: {word_row['letter_count']}  →  {blank}", style="cyan bold")
    console.print(Panel(body, title="[bold blue]Review[/bold blue]", border_style="blue"))


def show_review_outcome(word: str, correct: bool, console: Console) -> None:
    if correct:
        console.print(f"  [green]✓ Correct![/green]  The word was [bold]{word.upper()}[/bold]")
    else:
        console.print(f"  [red]✗ Wrong.[/red]  The word was [bold]{word.upper()}[/bold]")


def show_already_played(row, console: Console) -> None:
    result = "Correct" if row["guessed"] else "Failed"
    color = "green" if row["guessed"] else "red"
    body = (
        f"[{color}]{result}[/{color}] · {row['tries_used']} "
        + ("try" if row["tries_used"] == 1 else "tries")
        + f"  ·  Word: [bold]{row['word'].upper()}[/bold]"
    )
    console.print(
        Panel(body, title="[bold]Already played today[/bold]", border_style="dim")
    )


_PHONETIC_GUIDE = (
    "[bold yellow]Phonetic key:[/bold yellow]  "
    "UPPERCASE = stressed syllable  ·  hyphens separate syllables\n"
    "Common sounds:  [cyan]ay[/cyan]=ace  [cyan]a[/cyan]=at  [cyan]ah[/cyan]=father  "
    "[cyan]aw[/cyan]=law  [cyan]ee[/cyan]=easy  [cyan]i[/cyan]=hit  [cyan]eye[/cyan]=ice  "
    "[cyan]oh[/cyan]=go  [cyan]oo[/cyan]=rule  [cyan]ow[/cyan]=now  [cyan]oy[/cyan]=boy  "
    "[cyan]uh[/cyan]=up  [cyan]sh[/cyan]=shy  [cyan]ch[/cyan]=chin  [cyan]th[/cyan]=thin  "
    "[cyan]zh[/cyan]=vision  [cyan]ng[/cyan]=sing"
)


def show_examples(entry_or_row, console: Console) -> None:
    pronunciation = _get(entry_or_row, "pronunciation")
    examples_raw = _get(entry_or_row, "examples")
    did_you_know = _get(entry_or_row, "did_you_know")

    lines: list[Text] = []

    if pronunciation:
        lines.append(Text(f"Pronunciation:  {pronunciation}", style="bold white"))
        lines.append(Text(_PHONETIC_GUIDE))
        lines.append(Text(""))

    if examples_raw:
        lines.append(Text("Examples:", style="bold yellow"))
        for ex in examples_raw.split("\n"):
            ex = ex.strip()
            if ex:
                lines.append(Text(f"  • {ex}", style="white"))
        lines.append(Text(""))

    if did_you_know:
        lines.append(Text("Did you know?", style="bold yellow"))
        lines.append(Text(did_you_know, style="white"))

    if not lines:
        console.print("[dim]No extra information available.[/dim]")
        return

    body = Text("\n").join(lines)
    console.print(Panel(body, title="[bold]More Info[/bold]", border_style="yellow"))


def _get(obj, key: str) -> str:
    if isinstance(obj, dict) or hasattr(obj, "keys"):
        return obj[key] if key in obj.keys() else ""
    return getattr(obj, key, "")


def show_stats(stats: dict, console: Console) -> None:
    body = (
        f"[cyan]Words collected:[/cyan] {stats['total_words']}  · "
        f"[cyan]Total reviews:[/cyan] {stats['total_reviews']}  · "
        f"[cyan]Daily streak:[/cyan] {stats['daily_streak']} day(s)"
    )
    console.print(Panel(body, title="[bold]Stats[/bold]", border_style="dim"))
