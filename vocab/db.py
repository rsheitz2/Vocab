import sqlite3
from datetime import date, timedelta
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "vocab.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS words (
    word            TEXT PRIMARY KEY,
    date            TEXT NOT NULL,
    definition      TEXT NOT NULL,
    part_of_speech  TEXT NOT NULL,
    letter_count    INTEGER NOT NULL,
    pronunciation   TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS daily_games (
    date        TEXT PRIMARY KEY,
    word        TEXT NOT NULL,
    completed   INTEGER NOT NULL DEFAULT 0,
    guessed     INTEGER,
    tries_used  INTEGER,
    FOREIGN KEY (word) REFERENCES words(word)
);

CREATE TABLE IF NOT EXISTS review_queue (
    word            TEXT PRIMARY KEY,
    next_review     TEXT NOT NULL,
    interval_days   INTEGER NOT NULL DEFAULT 1,
    last_result     TEXT,
    review_count    INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (word) REFERENCES words(word)
);
"""


def init_db(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    _migrate(conn)
    conn.commit()
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(words)")}
    if "pronunciation" not in existing:
        conn.execute("ALTER TABLE words ADD COLUMN pronunciation TEXT NOT NULL DEFAULT ''")


def upsert_word(conn: sqlite3.Connection, entry) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO words (word, date, definition, part_of_speech, letter_count, pronunciation) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (entry.word, entry.date.isoformat(), entry.definition, entry.part_of_speech, entry.letter_count, entry.pronunciation),
    )
    conn.commit()


def seed_review_queue(conn: sqlite3.Connection, word: str, wotd_date: date) -> None:
    next_review = (wotd_date + timedelta(days=1)).isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO review_queue (word, next_review, interval_days) VALUES (?, ?, 1)",
        (word, next_review),
    )
    conn.commit()


def get_daily_game(conn: sqlite3.Connection, game_date: date) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM daily_games WHERE date = ?", (game_date.isoformat(),)
    ).fetchone()


def save_daily_game(
    conn: sqlite3.Connection, game_date: date, word: str, guessed: bool, tries_used: int
) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO daily_games (date, word, completed, guessed, tries_used) "
        "VALUES (?, ?, 1, ?, ?)",
        (game_date.isoformat(), word, 1 if guessed else 0, tries_used),
    )
    conn.commit()


def get_due_reviews(conn: sqlite3.Connection, today: date) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT r.word, r.next_review, r.interval_days, r.last_result, r.review_count, "
        "w.definition, w.part_of_speech, w.letter_count "
        "FROM review_queue r JOIN words w ON r.word = w.word "
        "WHERE r.next_review <= ? ORDER BY r.next_review",
        (today.isoformat(),),
    ).fetchall()


def update_review(conn: sqlite3.Connection, word: str, correct: bool) -> None:
    row = conn.execute(
        "SELECT interval_days FROM review_queue WHERE word = ?", (word,)
    ).fetchone()
    if row is None:
        return
    current = row["interval_days"]
    new_interval = min(current * 2, 60) if correct else max(current // 2, 1)
    next_review = (date.today() + timedelta(days=new_interval)).isoformat()
    conn.execute(
        "UPDATE review_queue SET interval_days = ?, next_review = ?, last_result = ?, "
        "review_count = review_count + 1 WHERE word = ?",
        (new_interval, next_review, "correct" if correct else "wrong", word),
    )
    conn.commit()


def get_word(conn: sqlite3.Connection, word: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM words WHERE word = ?", (word,)).fetchone()


def get_stats(conn: sqlite3.Connection) -> dict:
    total_words = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
    total_reviews = conn.execute("SELECT SUM(review_count) FROM review_queue").fetchone()[0] or 0

    rows = conn.execute(
        "SELECT date FROM daily_games WHERE completed = 1 ORDER BY date DESC"
    ).fetchall()
    streak = 0
    check = date.today()
    for row in rows:
        if row["date"] == check.isoformat():
            streak += 1
            check = check - timedelta(days=1)
        else:
            break

    return {"total_words": total_words, "total_reviews": total_reviews, "daily_streak": streak}
