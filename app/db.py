"""Local SQLite storage: schema, migrations, load and save."""

import json
import sqlite3
from datetime import date, datetime


class DataMixin:
    """Local SQLite storage: schema, migrations, load and save."""

    # -------------------------- data and theme --------------------------

    # Every scalar stat lives as a key/value row in `meta`; everything else
    # (notes, flashcards, quiz history, daily activity, badges, subjects
    # studied) gets its own relational table.
    _META_KEYS = ("study_minutes", "sessions", "flashcards_reviewed", "quizzes_taken",
                  "daily_goal", "xp", "level", "streak_days", "last_active_date",
                  "questions_asked", "decks_generated", "pdfs_created", "today_log",
                  "recent_topics", "teaching_language")

    _SCHEMA = """
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY CHECK (id = 1), name TEXT, avatar TEXT, pin_hash TEXT);
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY, title TEXT, content TEXT, created TEXT, updated TEXT);
        CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT, answer TEXT, subject TEXT,
            box INTEGER DEFAULT 1, due TEXT);
        CREATE TABLE IF NOT EXISTS quiz_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT, score INTEGER, taken_at TEXT);
        CREATE TABLE IF NOT EXISTS activity (day TEXT PRIMARY KEY, minutes INTEGER);
        CREATE TABLE IF NOT EXISTS badges (id TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS subjects_used (subject TEXT PRIMARY KEY);
    """

    def init_db(self):
        """Opens (or creates) the local SQLite database that now backs every
        save. If an older studygenie_data.json sits next to the app and the
        database is still empty, its contents are imported once so nobody
        loses their notes, decks, or streak by upgrading."""
        # check_same_thread=False: the Flet app saves from worker threads
        # (its callers serialise writes with a lock).
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.executescript(self._SCHEMA)
        # Databases made by older versions are missing some newer columns.
        self._add_missing_columns("notes", {"updated": "TEXT"})
        self._add_missing_columns("flashcards", {"box": "INTEGER DEFAULT 1", "due": "TEXT", "topic": "TEXT"})
        self.conn.commit()
        is_empty = self.conn.execute("SELECT COUNT(*) FROM meta").fetchone()[0] == 0
        if is_empty and self.legacy_json_path.exists():
            try:
                legacy = json.loads(self.legacy_json_path.read_text(encoding="utf-8"))
                if isinstance(legacy, dict):
                    merged = self.default_data()
                    merged.update(legacy)
                    self._write_all(merged)
            except (json.JSONDecodeError, OSError, sqlite3.Error):
                pass

    def _add_missing_columns(self, table, columns):
        """Adds any of `columns` ({name: sql type}) that `table` doesn't have yet."""
        existing = {row[1] for row in self.conn.execute(f"PRAGMA table_info({table})")}
        for name, sql_type in columns.items():
            if name not in existing:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")

    _LEGACY_NOTE_TIME = "%d %b %Y, %H:%M"

    @classmethod
    def _parse_note_time(cls, value):
        """Reads a note timestamp in either the current ISO format or the
        older display format. Unreadable values sort first instead of crashing."""
        if not value:
            return datetime.min
        for parse in (datetime.fromisoformat,
                      lambda v: datetime.strptime(v, cls._LEGACY_NOTE_TIME)):
            try:
                return parse(value)
            except (ValueError, TypeError):
                continue
        return datetime.min

    @classmethod
    def _note_time_label(cls, value):
        """Formats a stored note timestamp for display."""
        parsed = cls._parse_note_time(value)
        return parsed.strftime(cls._LEGACY_NOTE_TIME) if parsed != datetime.min else (value or "")

    def default_data(self):
        return {
            "notes": [], "flashcards": [], "study_minutes": 0, "sessions": 0,
            "flashcards_reviewed": 0, "quizzes_taken": 0, "quiz_scores": [],
            "activity": {}, "daily_goal": 60,
            "xp": 0, "level": 1, "streak_days": 0, "last_active_date": None,
            "badges": [], "questions_asked": 0, "subjects_used": [], "decks_generated": 0,
            "pdfs_created": 0,
            "today_log": {},  # {"date": iso day, "cards": n, "quizzes": n, ...}, reset each day
            "recent_topics": [],  # newest first: {"subject", "topic", "at"}
            "teaching_language": "English",  # the language the AI teaches in (not the interface)
            "teaching_language": "English",  # the language the AI teaches in (not the interface)
            "teaching_language": "English",  # the language the AI teaches in (not the interface)
            "profile": None,
        }

    def load_data(self):
        data = self.default_data()
        try:
            cur = self.conn.cursor()
            for key, value in cur.execute("SELECT key, value FROM meta"):
                try:
                    data[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    data[key] = value
            row = cur.execute("SELECT name, avatar, pin_hash FROM profile WHERE id = 1").fetchone()
            if row:
                data["profile"] = {"name": row[0], "avatar": row[1], "pin_hash": row[2]}
            # Sorted in Python, not SQL: older notes store `created` as display
            # text ("07 Nov 2026, 14:20"), which SQL would sort alphabetically.
            data["notes"] = sorted(
                ({"id": r[0], "title": r[1], "content": r[2], "created": r[3], "updated": r[4]}
                 for r in cur.execute("SELECT id, title, content, created, updated FROM notes")),
                key=lambda n: self._parse_note_time(n["created"]))
            data["flashcards"] = [{"question": r[0], "answer": r[1], "subject": r[2],
                                   "box": r[3] or 1, "due": r[4], "topic": r[5] or ""}
                                  for r in cur.execute(
                                      "SELECT question, answer, subject, box, due, topic FROM flashcards ORDER BY id")]
            data["quiz_scores"] = [r[0] for r in cur.execute("SELECT score FROM quiz_scores ORDER BY id")]
            data["activity"] = {r[0]: r[1] for r in cur.execute("SELECT day, minutes FROM activity")}
            data["badges"] = [r[0] for r in cur.execute("SELECT id FROM badges")]
            data["subjects_used"] = [r[0] for r in cur.execute("SELECT subject FROM subjects_used")]
        except sqlite3.Error as exc:
            self._last_db_error = str(exc)
        return data

    def save_data(self):
        """Persists self.data and returns True/False so callers (like the
        My Notes save button) can tell the user when a save actually
        failed instead of assuming silent success."""
        return self._write_all(self.data)

    def _write_all(self, data):
        """Persists the whole in-memory `data` dict to SQLite in one
        transaction — simple and safe, since every mutation in the app
        already goes through this same self.data dict before saving.
        Returns True on success, False (and records the error) on failure,
        so a save can surface a real message instead of failing silently."""
        try:
            cur = self.conn.cursor()
            for key in self._META_KEYS:
                cur.execute(
                    "INSERT INTO meta (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, json.dumps(data.get(key))))
            profile = data.get("profile")
            if profile:
                cur.execute(
                    "INSERT INTO profile (id, name, avatar, pin_hash) VALUES (1, ?, ?, ?) "
                    "ON CONFLICT(id) DO UPDATE SET name=excluded.name, avatar=excluded.avatar, "
                    "pin_hash=excluded.pin_hash",
                    (profile.get("name"), profile.get("avatar"), profile.get("pin_hash")))
            cur.execute("DELETE FROM notes")
            cur.executemany("INSERT INTO notes (id, title, content, created, updated) VALUES (?, ?, ?, ?, ?)",
                            [(str(n["id"]), n["title"], n["content"], n.get("created"), n.get("updated"))
                             for n in data.get("notes", [])])
            cur.execute("DELETE FROM flashcards")
            cur.executemany("INSERT INTO flashcards (question, answer, subject, box, due, topic) "
                            "VALUES (?, ?, ?, ?, ?, ?)",
                            [(c["question"], c["answer"], c.get("subject", "General"),
                              int(c.get("box") or 1), c.get("due"), c.get("topic") or "")
                             for c in data.get("flashcards", [])])
            cur.execute("DELETE FROM quiz_scores")
            cur.executemany("INSERT INTO quiz_scores (score, taken_at) VALUES (?, ?)",
                            [(s, "") for s in data.get("quiz_scores", [])])
            cur.execute("DELETE FROM activity")
            cur.executemany("INSERT INTO activity (day, minutes) VALUES (?, ?)",
                            list(data.get("activity", {}).items()))
            cur.execute("DELETE FROM badges")
            cur.executemany("INSERT INTO badges (id) VALUES (?)",
                            [(b,) for b in data.get("badges", [])])
            cur.execute("DELETE FROM subjects_used")
            cur.executemany("INSERT INTO subjects_used (subject) VALUES (?)",
                            [(s,) for s in data.get("subjects_used", [])])
            self.conn.commit()
            self._last_db_error = None
            return True
        except sqlite3.Error as exc:
            try:
                self.conn.rollback()
            except sqlite3.Error:
                pass
            self._last_db_error = str(exc)
            return False

    def today_key(self):
        return date.today().isoformat()

    def activity_today(self):
        return int(self.data["activity"].get(self.today_key(), 0))
