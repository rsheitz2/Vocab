# Vocab

A daily CLI word-guessing game powered by [Merriam-Webster's Word of the Day](https://www.merriam-webster.com/word-of-the-day).

## How to play

Each day you get a new word to guess. You're shown the **definition** and the **number of letters**. You have **3 tries**, and a new hint is revealed after each wrong guess:

| Try | Hints shown |
|-----|-------------|
| 1 | Definition + blanks (e.g. `_ _ _ _ _`) |
| 2 | + Part of speech (e.g. *noun*) |
| 3 | + First letter (e.g. `N _ _ _ _`) |

At any guess prompt you can use these commands instead of guessing — they don't cost a try:

| Command | Action |
|---------|--------|
| `p` | Play the word's pronunciation aloud |
| `e` | Show usage examples, a phonetic sound key, and the word's etymology |

## Review mode

After the daily game, past words due for review appear automatically — **1 try each**. The same `p` and `e` commands are available during review.

- **Correct** → word comes back later (interval doubles, max 60 days)
- **Wrong** → word comes back sooner (interval halves, min 1 day)

Words start with a 1-day interval (reviewed the day after you first see them).

## Setup & run

```bash
cd ~/Documents/Projects/Vocab
uv sync
```

Then use the included script:

```bash
./vocab.sh          # show help
./vocab.sh start    # play today's game
```

## Run tests

```bash
uv run pytest tests/ -v -m "not network"   # offline unit tests
uv run pytest tests/ -v -m network         # live M-W RSS fetch test
```

## Project structure

```
app.py          Entry point / orchestrator
vocab/
  db.py         SQLite layer (words, daily_games, review_queue)
  fetcher.py    M-W RSS fetch + parse → WordEntry
  game.py       Daily 3-try game loop
  review.py     Spaced-repetition review session
  display.py    All rich terminal rendering
data/vocab.db   Auto-created SQLite database
```
