import json
import sqlite3
import unittest
from datetime import datetime

from app.db import DataMixin
from tests.helpers import AppTestCase


class StorageTests(AppTestCase, unittest.TestCase):
    def test_fresh_database_loads_defaults(self):
        self.assertEqual(self.app.data["level"], 1)
        self.assertEqual(self.app.data["notes"], [])
        self.assertIsNone(self.app.data["profile"])

    def test_everything_survives_a_restart(self):
        d = self.app.data
        d.update(xp=42, level=3, streak_days=4, last_active_date="2026-11-07", daily_goal=45)
        d["profile"] = {"name": "Sam", "avatar": "🦊", "pin_hash": "abc"}
        d["notes"].append({"id": "n1", "title": "Cells", "content": "Mitochondria",
                           "created": "2026-11-07T10:00:00", "updated": None})
        d["flashcards"].append({"question": "2+2", "answer": "4", "subject": "Maths",
                                "box": 3, "due": "2026-11-10"})
        d["quiz_scores"] = [80, 100]
        d["activity"] = {"2026-11-07": 25}
        d["badges"] = ["first_session"]
        d["subjects_used"] = ["Maths", "Biology"]
        self.assertTrue(self.app.save_data())

        loaded = self.reopen().data
        self.assertEqual(loaded["xp"], 42)
        self.assertEqual(loaded["level"], 3)
        self.assertEqual(loaded["last_active_date"], "2026-11-07")
        self.assertEqual(loaded["profile"], {"name": "Sam", "avatar": "🦊", "pin_hash": "abc"})
        self.assertEqual(loaded["notes"][0]["content"], "Mitochondria")
        self.assertEqual(loaded["flashcards"][0]["box"], 3)
        self.assertEqual(loaded["flashcards"][0]["due"], "2026-11-10")
        self.assertEqual(loaded["quiz_scores"], [80, 100])
        self.assertEqual(loaded["activity"], {"2026-11-07": 25})
        self.assertEqual(loaded["badges"], ["first_session"])
        self.assertEqual(sorted(loaded["subjects_used"]), ["Biology", "Maths"])

    def test_notes_with_mixed_date_formats_load_oldest_first(self):
        self.app.data["notes"] = [
            {"id": "new", "title": "b", "content": "x", "created": "2026-11-08T09:00:00"},
            {"id": "old", "title": "a", "content": "x", "created": "07 Nov 2026, 14:20"},
            {"id": "bad", "title": "c", "content": "x", "created": "garbage"},
        ]
        self.app.save_data()
        self.assertEqual([n["id"] for n in self.reopen().data["notes"]], ["bad", "old", "new"])

    def test_save_failure_returns_false_and_records_error(self):
        self.app.conn.close()
        self.assertFalse(self.app.save_data())
        self.assertTrue(self.app._last_db_error)


class MigrationTests(AppTestCase, unittest.TestCase):
    def make_app(self):
        # Write the legacy file before the first app opens the empty database.
        if not self.db_path.exists():
            self.json_path.write_text(json.dumps({
                "xp": 77, "streak_days": 5,
                "notes": [{"id": 1700000000, "title": "Old", "content": "from json",
                           "created": "01 Jan 2026, 09:00"}],
                "flashcards": [{"question": "q", "answer": "a"}],
            }), encoding="utf-8")
        return super().make_app()

    def test_legacy_json_is_imported_once(self):
        d = self.app.data
        self.assertEqual(d["xp"], 77)
        self.assertEqual(d["streak_days"], 5)
        self.assertEqual(d["notes"][0]["id"], "1700000000")
        self.assertEqual(d["flashcards"][0]["box"], 1)

        # Changes made after migration must not be overwritten by the JSON.
        d["xp"] = 5
        self.app.save_data()
        self.assertEqual(self.reopen().data["xp"], 5)


class OldSchemaTests(AppTestCase, unittest.TestCase):
    def make_app(self):
        if not self.db_path.exists():
            conn = sqlite3.connect(self.db_path)
            conn.executescript("""
                CREATE TABLE notes (id TEXT PRIMARY KEY, title TEXT, content TEXT, created TEXT);
                CREATE TABLE flashcards (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                         question TEXT, answer TEXT, subject TEXT);
                INSERT INTO flashcards (question, answer, subject) VALUES ('q', 'a', 'General');
            """)
            conn.commit()
            conn.close()
        return super().make_app()

    def test_missing_columns_are_added(self):
        card = self.app.data["flashcards"][0]
        self.assertEqual(card["box"], 1)
        self.assertIsNone(card["due"])
        self.app.data["notes"].append({"id": "n", "title": "t", "content": "c",
                                       "created": None, "updated": "2026-11-08T10:00:00"})
        self.assertTrue(self.app.save_data())


class NoteTimeTests(unittest.TestCase):
    def test_parses_iso_and_legacy_formats(self):
        self.assertEqual(DataMixin._parse_note_time("2026-11-08T09:30:00"), datetime(2026, 11, 8, 9, 30))
        self.assertEqual(DataMixin._parse_note_time("07 Nov 2026, 14:20"), datetime(2026, 11, 7, 14, 20))

    def test_unreadable_values_sort_first(self):
        for value in (None, "", "soon"):
            self.assertEqual(DataMixin._parse_note_time(value), datetime.min)

    def test_label(self):
        self.assertEqual(DataMixin._note_time_label("2026-11-08T09:30:00"), "08 Nov 2026, 09:30")
        self.assertEqual(DataMixin._note_time_label("soon"), "soon")
        self.assertEqual(DataMixin._note_time_label(None), "")


if __name__ == "__main__":
    unittest.main()
