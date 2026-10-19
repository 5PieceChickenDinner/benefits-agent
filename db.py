import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "benefits.db"


@contextmanager
def connect():
    """Open a connection for one unit of work, committing on success."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:  # commits on success, rolls back on error
            yield conn
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id         TEXT PRIMARY KEY,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL REFERENCES conversations(id),
                role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content         TEXT NOT NULL,
                created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages (conversation_id, id);
            """
        )


def create_conversation() -> str:
    conversation_id = str(uuid.uuid4())
    with connect() as conn:
        conn.execute("INSERT INTO conversations (id) VALUES (?)", (conversation_id,))
    return conversation_id


def conversation_exists(conversation_id: str) -> bool:
    with connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
    return row is not None


def get_messages(conversation_id: str, limit: int | None = None) -> list[dict]:
    """Return messages oldest-first; with a limit, only the most recent ones."""
    query = "SELECT role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY id DESC"
    params: tuple = (conversation_id,)
    if limit is not None:
        query += " LIMIT ?"
        params += (limit,)
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in reversed(rows)]


def add_exchange(conversation_id: str, question: str, answer: str) -> None:
    """Save a question and its answer together, in one transaction."""
    with connect() as conn:
        conn.executemany(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            [
                (conversation_id, "user", question),
                (conversation_id, "assistant", answer),
            ],
        )
