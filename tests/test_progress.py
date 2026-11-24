import unittest
from datetime import date, timedelta

from app.profile import hash_pin
from tests.helpers import AppTestCase


class XpAndLevelTests(AppTestCase, unittest.TestCase):
    def test_xp_needed_grows_per_level(self):
        self.assertEqual(self.app.xp_for_level(1), 100)
        self.assertEqual(self.app.xp_for_level(2), 160)
        self.assertEqual(self.app.xp_for_level(5), 340)

    def test_small_gain_does_not_level_up(self):
        self.app.add_xp(50)
        self.assertEqual((self.app.data["level"], self.app.data["xp"]), (1, 50))
        self.assertEqual(self.app.celebrations, [])

    def test_big_gain_can_skip_several_levels(self):
        self.app.add_xp(100 + 160 + 10)  # through level 1 and 2, 10 into level 3
        self.assertEqual((self.app.data["level"], self.app.data["xp"]), (3, 10))
        self.assertEqual(self.app.celebrations, ["Level 3!"])

    def test_xp_is_saved(self):
        self.app.add_xp(30)
        self.assertEqual(self.reopen().data["xp"], 30)


class StreakTests(AppTestCase, unittest.TestCase):
    def set_last_active(self, days_ago, streak):
        self.app.data["last_active_date"] = (date.today() - timedelta(days=days_ago)).isoformat()
        self.app.data["streak_days"] = streak

    def test_first_ever_day_starts_at_one(self):
        self.app.update_streak()
        self.assertEqual(self.app.data["streak_days"], 1)
        self.assertEqual(self.app.data["last_active_date"], date.today().isoformat())

    def test_same_day_does_not_double_count(self):
        self.set_last_active(0, 4)
        self.app.update_streak()
        self.assertEqual(self.app.data["streak_days"], 4)

    def test_consecutive_day_extends(self):
        self.set_last_active(1, 4)
        self.app.update_streak()
        self.assertEqual(self.app.data["streak_days"], 5)

    def test_missed_day_resets(self):
        self.set_last_active(3, 9)
        self.app.update_streak()
        self.assertEqual(self.app.data["streak_days"], 1)


class StudyMinutesAndBadgeTests(AppTestCase, unittest.TestCase):
    def test_study_minutes_add_activity_streak_and_xp(self):
        self.app.add_study_minutes(25)
        d = self.app.data
        self.assertEqual(d["study_minutes"], 25)
        self.assertEqual(d["activity"][date.today().isoformat()], 25)
        self.assertEqual(d["streak_days"], 1)
        self.assertEqual(d["xp"], 50)

    def test_badges_unlock_once(self):
        self.app.data["sessions"] = 1
        first = self.app.check_badges()
        self.assertEqual([b["id"] for b in first], ["first_session"])
        self.assertEqual(self.app.check_badges(), [])
        self.assertEqual(self.app.data["badges"], ["first_session"])

    def test_quiz_ace_and_flawless(self):
        self.app.data["quiz_scores"] = [100]
        ids = {b["id"] for b in self.app.check_badges()}
        self.assertTrue({"quiz_ace", "flawless"} <= ids)

    def test_track_subject_ignores_repeats_and_blanks(self):
        for s in ("Maths", "Maths", "", None, "Physics"):
            self.app.track_subject(s)
        self.assertEqual(self.app.data["subjects_used"], ["Maths", "Physics"])


class NoteTests(AppTestCase, unittest.TestCase):
    def test_add_note_saves_and_awards_xp(self):
        self.assertTrue(self.app.add_note("  Cells  ", "  Mitochondria  "))
        note = self.reopen().data["notes"][0]
        self.assertEqual((note["title"], note["content"]), ("Cells", "Mitochondria"))
        self.assertEqual(self.app.data["xp"], 2)

    def test_blank_title_becomes_untitled(self):
        self.app.add_note("   ", "body")
        self.assertEqual(self.app.data["notes"][0]["title"], "Untitled note")

    def test_empty_content_is_rejected(self):
        self.assertFalse(self.app.add_note("Title", "   "))
        self.assertEqual(self.app.data["notes"], [])

    def test_failed_save_rolls_back(self):
        self.app.conn.close()
        self.assertFalse(self.app.add_note("Title", "body"))
        self.assertEqual(self.app.data["notes"], [])

    def test_note_ids_are_unique(self):
        for i in range(20):
            self.app.add_note(f"n{i}", "body")
        ids = [n["id"] for n in self.app.data["notes"]]
        self.assertEqual(len(ids), len(set(ids)))


class LevelTitleAndQuestTests(AppTestCase, unittest.TestCase):
    def test_level_titles(self):
        self.assertEqual(self.app.level_title(1), "Beginner")
        self.assertEqual(self.app.level_title(5), "Scholar")
        self.assertEqual(self.app.level_title(6), "Scholar")
        self.assertEqual(self.app.level_title(5, with_icon=True), "Scholar 🧠")
        self.assertEqual(self.app.level_title(99), "Legend")

    def test_total_xp_counts_completed_levels(self):
        self.app.data.update(level=3, xp=10)
        self.assertEqual(self.app.total_xp(), 100 + 160 + 10)

    def test_today_counts_reset_on_a_new_day(self):
        self.app.bump_today("cards", 3)
        self.app.bump_today("cards")
        self.assertEqual(self.app.today_count("cards"), 4)
        self.app.data["today_log"]["date"] = "2000-01-01"  # pretend it was logged long ago
        self.assertEqual(self.app.today_count("cards"), 0)
        self.app.bump_today("cards")
        self.assertEqual(self.app.today_count("cards"), 1)

    def test_today_log_survives_a_restart(self):
        self.app.bump_today("quizzes")
        self.app.save_data()
        self.assertEqual(self.reopen().today_count("quizzes"), 1)

    def test_daily_quests_cap_at_target(self):
        self.app.data["daily_goal"] = 30
        self.app.data["activity"][self.app.today_key()] = 45
        self.app.bump_today("cards", 25)
        focus, cards, quiz = self.app.daily_quests()
        self.assertEqual(focus, ("Focus for 30 minutes", 30, 30))
        self.assertEqual(cards[1:], (10, 10))
        self.assertEqual(quiz[1:], (0, 1))


class PinTests(unittest.TestCase):
    def test_hash_is_stable_and_not_the_pin(self):
        self.assertEqual(hash_pin("1234"), hash_pin("1234"))
        self.assertNotEqual(hash_pin("1234"), hash_pin("1235"))
        self.assertNotIn("1234", hash_pin("1234"))
        self.assertEqual(len(hash_pin("1234")), 64)


if __name__ == "__main__":
    unittest.main()
