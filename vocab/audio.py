import os
import subprocess
import tempfile

from rich.console import Console


def play_word(word: str, console: Console) -> None:
    try:
        from gtts import gTTS
        tts = gTTS(word, lang="en")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_path = f.name
        tts.save(tmp_path)
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", tmp_path],
            check=True,
        )
    except Exception as exc:
        console.print(f"[yellow]Could not play audio: {exc}[/yellow]")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
