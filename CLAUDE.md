# Vocab

CLI word-of-the-day game using Merriam-Webster's RSS feed with spaced repetition.

## Commands

```bash
./vocab.sh start                           # daily game, then due reviews
./vocab.sh review [--all]                  # reviews only; --all = every word, due or not
./vocab.sh history                         # vi-style word browser
./vocab.sh                                 # help (vocab.sh = uv run python app.py "$@")
uv run pytest tests/ -v -m "not network"   # unit tests (offline)
uv run pytest tests/ -v -m network         # live RSS fetch test
```

## Architecture

`app.py` is a thin orchestrator. All logic lives in `vocab/`:

| Module | Responsibility |
|--------|---------------|
| `db.py` | SQLite schema and CRUD (words, daily_games, review_queue) |
| `fetcher.py` | Fetch M-W RSS, parse WordEntry, seed DB |
| `game.py` | Daily game loop — 6 tries with progressive hints |
| `review.py` | Review session — 1 try per word |
| `display.py` | All `rich` terminal rendering, clue redaction, letter reveals |
| `history.py` | prompt_toolkit word browser (`p` plays audio in a thread) |
| `audio.py` | gTTS + ffplay pronunciation (`speak` raises, `play_word` prints errors) |
| `literature.py` | Google Books literary examples, cached in `words.literary_examples` |

## Data

`data/vocab.db` — auto-created on first run. Three tables:
- `words` — one row per WOTD ever fetched
- `daily_games` — one row per calendar day played
- `review_queue` — spaced repetition state per word

## Spaced Repetition

Correct: `interval = min(interval * 2, 60)`. Wrong: `interval = max(interval // 2, 1)`.  
Words start with `interval_days = 1` (review next day after first encounter).

## Game mechanics

- Hints by try (`MAX_TRIES = 6` in `game.py`): definition + blanks → part of speech → first letter → last → second → middle. `_reveal_order` always leaves ≥1 letter hidden.
- Wrong guesses are shown Wordle-style via `score_guess()` (green/yellow/gray; exact matches claim duplicate letters first).
- `_redact()` blanks the word *and* inflections (-s/-ed/-ing/…, dropped-e, y→i, doubled consonant); blank is base-word length, suffix stays visible. Irregular forms (ran/run) are not caught.
- No phonetic pronunciation in clues — it gives the word away. Still available via `e` / `p`.
- `review --all` updates the spaced-repetition schedule like a normal review.

## Gotchas

- At guess prompts `p` and `e` are commands, not guesses — don't use them as wrong-guess inputs in tests.
- Never smoke-test reviews/games against `data/vocab.db`: answers rewrite `review_queue`. Use a temp DB (`init_db(tmp_path / "x.db")`).

## Workflow

Commit and push directly to `master` (solo project), only when asked.
