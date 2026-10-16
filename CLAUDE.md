# Vocab

CLI word-of-the-day game using Merriam-Webster's RSS feed with spaced repetition.

## Commands

```bash
uv run python app.py                        # play the game
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
| `display.py` | All `rich` terminal rendering |

## Data

`data/vocab.db` — auto-created on first run. Three tables:
- `words` — one row per WOTD ever fetched
- `daily_games` — one row per calendar day played
- `review_queue` — spaced repetition state per word

## Spaced Repetition

Correct: `interval = min(interval * 2, 60)`. Wrong: `interval = max(interval // 2, 1)`.  
Words start with `interval_days = 1` (review next day after first encounter).
