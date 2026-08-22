import sqlite3
from pathlib import Path
from datetime import datetime, timezone


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "dariush.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            language TEXT DEFAULT 'fa',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_messages_user_id
        ON messages(user_id);

        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            memory TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_memories_user_id
        ON memories(user_id);

        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_notes_user_id
        ON notes(user_id);

        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            remind_at TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            daily INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_reminders_user_id
        ON reminders(user_id);

        CREATE INDEX IF NOT EXISTS idx_reminders_due
        ON reminders(remind_at, completed);
        """)
    
    # Ensure scheduled-note columns exist for both
    # existing and newly created databases.
    ensure_note_schedule_columns()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def upsert_user(user_id, username=None, first_name=None):
    timestamp = now_iso()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (
                user_id, username, first_name, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                updated_at = excluded.updated_at
            """,
            (user_id, username, first_name, timestamp, timestamp),
        )


def save_message(user_id, role, content):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO messages (
                user_id, role, content, created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (user_id, role, content, now_iso()),
        )


def get_recent_messages(user_id, limit=20):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT role, content
            FROM messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    return list(reversed(rows))


def add_memory(user_id, memory):
    timestamp = now_iso()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO memories (
                user_id, memory, created_at, updated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (user_id, memory, timestamp, timestamp),
        )


def get_memories(user_id, limit=20):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, memory, created_at, updated_at
            FROM memories
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()


def delete_memory(user_id, memory_id):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            DELETE FROM memories
            WHERE id = ? AND user_id = ?
            """,
            (memory_id, user_id),
        )

        return cursor.rowcount > 0



def ensure_note_schedule_columns():
    with get_connection() as conn:
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(notes)").fetchall()
        }

        if "scheduled_at" not in columns:
            conn.execute(
                "ALTER TABLE notes ADD COLUMN scheduled_at TEXT"
            )

        if "schedule_enabled" not in columns:
            conn.execute(
                "ALTER TABLE notes ADD COLUMN schedule_enabled INTEGER DEFAULT 0"
            )


def add_note(
    user_id,
    content,
    title=None,
    scheduled_at=None,
    schedule_enabled=False,
):
    timestamp = now_iso()

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO notes (
                user_id,
                title,
                content,
                created_at,
                updated_at,
                scheduled_at,
                schedule_enabled
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                title,
                content,
                timestamp,
                timestamp,
                scheduled_at,
                1 if schedule_enabled else 0,
            ),
        )

        return cursor.lastrowid


def get_notes(user_id, limit=50):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT
                id,
                title,
                content,
                created_at,
                updated_at,
                scheduled_at,
                schedule_enabled
            FROM notes
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()


def delete_note(user_id, note_id):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            DELETE FROM notes
            WHERE id = ? AND user_id = ?
            """,
            (note_id, user_id),
        )

        return cursor.rowcount > 0



def get_due_scheduled_notes():
    current_time = now_iso()

    with get_connection() as conn:
        return conn.execute(
            """
            SELECT
                id,
                user_id,
                content,
                scheduled_at
            FROM notes
            WHERE schedule_enabled = 1
              AND scheduled_at IS NOT NULL
              AND scheduled_at <= ?
            ORDER BY scheduled_at ASC
            """,
            (current_time,),
        ).fetchall()


def mark_note_schedule_completed(note_id):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE notes
            SET schedule_enabled = 0,
                updated_at = ?
            WHERE id = ?
            """,
            (now_iso(), note_id),
        )

        return cursor.rowcount > 0

def add_reminder(user_id, text, remind_at):
    timestamp = now_iso()

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO reminders (
                user_id, text, remind_at, created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (user_id, text, remind_at, timestamp),
        )

        return cursor.lastrowid


def get_pending_reminders(user_id):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, text, remind_at
            FROM reminders
            WHERE user_id = ? AND completed = 0
            ORDER BY remind_at ASC
            """,
            (user_id,),
        ).fetchall()


def get_due_reminders():
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, user_id, text, remind_at
            FROM reminders
            WHERE completed = 0
              AND remind_at <= ?
            ORDER BY remind_at ASC
            """,
            (now_iso(),),
        ).fetchall()


def complete_reminder(reminder_id):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE reminders
            SET completed = 1
            WHERE id = ?
            """,
            (reminder_id,),
        )


def get_daily_reminders():
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, user_id, text, remind_at
            FROM reminders
            WHERE completed = 0
              AND daily = 1
            ORDER BY remind_at ASC
            """
        ).fetchall()


def set_reminder_daily(user_id, reminder_id, enabled):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE reminders
            SET daily = ?
            WHERE id = ? AND user_id = ?
            """,
            (1 if enabled else 0, reminder_id, user_id),
        )
        return cursor.rowcount > 0


def delete_reminder(user_id, reminder_id):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            DELETE FROM reminders
            WHERE id = ? AND user_id = ?
            """,
            (reminder_id, user_id),
        )
        return cursor.rowcount > 0


def get_reminder(user_id, reminder_id):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, user_id, text, remind_at, completed, daily
            FROM reminders
            WHERE id = ? AND user_id = ?
            """,
            (reminder_id, user_id),
        ).fetchone()


def get_due_daily_reminders():
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, user_id, text, remind_at, daily
            FROM reminders
            WHERE completed = 0
              AND daily = 1
              AND remind_at <= ?
            ORDER BY remind_at ASC
            """,
            (now_iso(),),
        ).fetchall()


def update_reminder_time(reminder_id, user_id, remind_at):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE reminders
            SET remind_at = ?
            WHERE id = ?
              AND user_id = ?
              AND completed = 0
            """,
            (remind_at, reminder_id, user_id),
        )
        return cursor.rowcount > 0


def advance_daily_reminder(reminder_id, current_remind_at):
    from datetime import datetime, timedelta

    try:
        dt = datetime.fromisoformat(current_remind_at)
    except ValueError:
        return False

    next_time = dt + timedelta(days=1)

    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE reminders
            SET remind_at = ?
            WHERE id = ?
              AND daily = 1
              AND completed = 0
            """,
            (next_time.isoformat(), reminder_id),
        )

    return cursor.rowcount > 0
