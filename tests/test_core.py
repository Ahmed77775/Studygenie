"""The window-free core used by the Flet app, and its friendly AI errors."""
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.ai_service import friendly_error
from app.core import StudyCore


class CoreTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="studygenie-core-"))
        self.core = StudyCore(self.tmp / "data.db", self.tmp / "none.json")
        self.events = []
        self.core.subscribe(lambda kind, info: self.events.append(kind))

    def tearDown(self):
        self.core.conn.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def reopen(self):
        self.core.conn.close()
        self.core = StudyCore(self.tmp / "data.db", self.tmp / "none.json")
        return self.core


class ProfileTests(CoreTestCase):
    def test_create_profile_with_pin(self):
        self.assertFalse(self.core.has_profile)
        self.core.create_profile("  Ahmed ", "🦉", "1234")
        core = self.reopen()
        self.assertEqual(core.data["profile"]["name"], "Ahmed")
        self.assertTrue(core.pin_matches("1234"))
        self.assertFalse(core.pin_matches("9999"))
        self.assertEqual(core.display_name, "Ahmed")

    def test_profile_validation(self):
        with self.assertRaises(ValueError):
            self.core.create_profile("  ", "🦉")
        with self.assertRaises(ValueError):
            self.core.create_profile("A", "🦉", "12")
        with self.assertRaises(ValueError):
            self.core.create_profile("A", "🦉", "12ab")

    def test_no_pin_always_matches(self):
        self.core.create_profile("Sam", "🐼")
        self.assertTrue(self.core.pin_matches(""))

    def test_guest_shows_as_student(self):
        self.core.profile = {"name": "Guest"}
        self.assertEqual(self.core.display_name, "Student")


class LearningFlowTests(CoreTestCase):
    def test_generated_cards_get_topic_and_drive_focus(self):
        items = [{"question": f"q{i}", "answer": "a"} for i in range(3)]
        self.core.add_generated_cards(items, "Physics", "Current Electricity")
        core = self.reopen()
        self.assertEqual({c["topic"] for c in core.data["flashcards"]}, {"Current Electricity"})
        focus = core.focus()
        self.assertEqual((focus["subject"], focus["topic"], focus["percent"], focus["due"]),
                         ("Physics", "Current Electricity", 0, 3))
        self.assertEqual(core.data["decks_generated"], 1)
        self.assertEqual(core.data["xp"], 8)

    def test_review_and_rate(self):
        self.core.add_card("2+2", "4", "Mathematics", "Addition")
        card = self.core.due_cards()[0]
        self.core.reveal_card()
        self.core.rate_card(card, True)
        self.assertEqual(card["box"], 2)
        self.assertEqual(self.core.due_cards(), [])
        self.assertEqual(self.core.today_count("cards"), 1)
        self.assertEqual(self.core.data["flashcards_reviewed"], 1)

    def test_due_cards_filter_by_topic(self):
        self.core.add_card("q1", "a", "Physics", "Optics")
        self.core.add_card("q2", "a", "Physics", "Magnetism")
        self.assertEqual([c["question"] for c in self.core.due_cards("optics")], ["q1"])

    def test_add_card_needs_both_sides(self):
        with self.assertRaises(ValueError):
            self.core.add_card("q", " ", "Physics")

    def test_finish_quiz(self):
        score = self.core.finish_quiz(4, 5)
        self.assertEqual(score, 80)
        core = self.reopen()
        self.assertEqual(core.data["quiz_scores"], [80])
        self.assertEqual(core.today_count("quizzes"), 1)
        self.assertEqual(core.data["streak_days"], 1)

    def test_photo_records_topic_and_xp(self):
        self.core.finish_photo("Mathematics", "Linear equations")
        self.assertEqual(self.core.data["recent_topics"][0]["topic"], "Linear equations")
        self.assertEqual(self.core.today_count("photos"), 1)
        self.assertEqual(self.core.data["xp"], 5)

    def test_questions_and_answers(self):
        self.core.count_question("Physics")
        self.core.finish_answer()
        self.assertEqual(self.core.data["questions_asked"], 1)
        self.assertIn("Physics", self.core.data["subjects_used"])
        self.assertEqual(self.core.data["xp"], 5)

    def test_focus_session(self):
        self.core.finish_focus_session(25)
        self.assertEqual(self.core.data["sessions"], 1)
        self.assertEqual(self.core.activity_today(), 25)
        self.assertIn("status", self.events)

    def test_level_info(self):
        self.core.data.update(level=3, xp=40)
        info = self.core.level_info()
        self.assertEqual((info["level"], info["title"], info["needed"], info["total"]), (3, "Learner", 220, 300))


class NoteTests(CoreTestCase):
    def test_update_and_delete(self):
        self.core.add_note("Cells", "Mitochondria")
        note_id = self.core.data["notes"][0]["id"]
        self.core.update_note(note_id, "Cells v2", "ATP")
        self.assertEqual(self.reopen().data["notes"][0]["content"], "ATP")
        self.core.delete_note(note_id)
        self.assertEqual(self.reopen().data["notes"], [])

    def test_empty_update_rejected(self):
        self.core.add_note("Cells", "Mitochondria")
        with self.assertRaises(ValueError):
            self.core.update_note(self.core.data["notes"][0]["id"], "x", "  ")

    def test_newest_first(self):
        self.core.data["notes"] = [{"id": "a", "title": "old", "content": "x", "created": "2026-01-01T10:00:00"},
                                   {"id": "b", "title": "new", "content": "x", "created": "2026-11-01T10:00:00"}]
        self.assertEqual([n["id"] for n in self.core.notes_newest_first()], ["b", "a"])


class TeachingLanguageTests(CoreTestCase):
    def test_default_is_english(self):
        self.assertEqual(self.core.teaching_language, "English")

    def test_choice_survives_a_restart(self):
        self.core.save_teaching_language("Telugu")
        self.assertEqual(self.reopen().teaching_language, "Telugu")

    def test_menu_labels_map_back(self):
        self.core.save_teaching_language("Kannada (experimental)")
        self.assertEqual(self.reopen().teaching_language, "Kannada")
        self.assertIn("Malayalam (experimental)", self.core.language_choices())
        self.assertIn("Hindi", self.core.language_choices())

    def test_unknown_values_are_ignored(self):
        self.core.save_teaching_language("Klingon")
        self.assertEqual(self.core.teaching_language, "English")
        self.core.data["teaching_language"] = "Klingon"  # e.g. an edited database
        self.assertEqual(self.core.teaching_language, "English")


class FriendlyErrorTests(unittest.TestCase):
    def test_messages(self):
        self.assertIn("Ollama", friendly_error(ConnectionError("Connection refused")))
        self.assertIn("ollama pull", friendly_error(Exception("model 'gemma3:4b' not found")))
        self.assertIn("incomplete", friendly_error(ValueError("The model did not return a JSON list")))
        self.assertNotIn("Traceback", friendly_error(KeyError("x")))


if __name__ == "__main__":
    unittest.main()
