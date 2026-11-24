import unittest
from datetime import date

from app import stats

TODAY = date(2026, 11, 8)  # a Sunday


class BoxCountTests(unittest.TestCase):
    def test_counts_every_box(self):
        cards = [{"box": 1}, {"box": 1}, {"box": 3}, {"box": 5}, {}]
        self.assertEqual(stats.box_counts(cards), {1: 3, 2: 0, 3: 1, 4: 0, 5: 1})

    def test_out_of_range_boxes_are_clamped(self):
        self.assertEqual(stats.box_counts([{"box": 9}, {"box": 0}]), {1: 1, 2: 0, 3: 0, 4: 0, 5: 1})


class ForecastTests(unittest.TestCase):
    def test_new_and_overdue_cards_count_today(self):
        cards = [{"due": None}, {"due": "2026-11-01"}, {"due": "2026-11-08"},
                 {"due": "2026-11-10"}, {"due": "2026-12-25"}, {"due": "oops"}]
        forecast = stats.due_forecast(cards, TODAY, days=7)
        self.assertEqual(forecast[0], (TODAY, 4))
        self.assertEqual(forecast[2], (date(2026, 11, 10), 1))
        self.assertEqual(sum(n for _, n in forecast), 5)  # Christmas is beyond the week
        self.assertEqual(len(forecast), 7)


class ActivityGridTests(unittest.TestCase):
    def test_shape_and_alignment(self):
        grid = stats.activity_grid({"2026-11-08": 30, "2026-11-02": 10}, TODAY, weeks=3)
        self.assertEqual(len(grid), 3)
        self.assertTrue(all(len(week) == 7 for week in grid))
        self.assertEqual(grid[0][0][0], date(2026, 10, 19))      # oldest cell is a Monday
        self.assertEqual(grid[-1][0], (date(2026, 11, 2), 10))   # this week's Monday
        self.assertEqual(grid[-1][6], (TODAY, 30))

    def test_future_days_are_blank(self):
        wednesday = date(2026, 11, 4)
        last_week = stats.activity_grid({}, wednesday, weeks=1)[0]
        self.assertEqual(last_week[2], (wednesday, 0))
        self.assertEqual(last_week[3:], [None] * 4)


class StreakTests(unittest.TestCase):
    def test_longest_run(self):
        activity = {"2026-11-01": 5, "2026-11-02": 5, "2026-11-03": 5,
                    "2026-11-05": 5, "2026-11-06": 5, "2026-11-04": 0}
        self.assertEqual(stats.best_streak(activity), 3)

    def test_empty_and_bad_keys(self):
        self.assertEqual(stats.best_streak({}), 0)
        self.assertEqual(stats.best_streak({"nonsense": 10, "2026-11-01": 1}), 1)


class SummaryTests(unittest.TestCase):
    def test_headline_numbers(self):
        data = {
            "flashcards": [{"box": 5, "due": "2026-11-20"}, {"box": 2, "due": None}, {"box": 1, "subject": "Maths"}],
            "activity": {"2026-11-07": 20, "2026-11-08": 15},
            "quiz_scores": [60, 90, 75],
            "study_minutes": 35,
            "streak_days": 2,
        }
        s = stats.summary(data, TODAY)
        self.assertEqual(s["due_today"], 2)
        self.assertEqual(s["total_cards"], 3)
        self.assertEqual(s["mastered"], 1)
        self.assertEqual(s["days_studied"], 2)
        self.assertEqual(s["best_streak"], 2)
        self.assertEqual((s["quizzes"], s["quiz_average"], s["quiz_best"]), (3, 75, 90))

    def test_empty_data(self):
        s = stats.summary({}, TODAY)
        self.assertEqual(s["total_cards"], 0)
        self.assertIsNone(s["quiz_average"])
        self.assertEqual(s["best_streak"], 0)

    def test_subject_counts(self):
        cards = [{"subject": "Maths"}, {"subject": "Bio"}, {"subject": "Maths"}, {}]
        self.assertEqual(stats.subject_counts(cards), [("Maths", 2), ("Bio", 1), ("General", 1)])


class SubjectMasteryTests(unittest.TestCase):
    def test_percent_from_boxes(self):
        cards = [{"subject": "Maths", "box": 5}, {"subject": "Maths", "box": 1},
                 {"subject": "Bio", "box": 3}, {"box": None}]
        self.assertEqual(stats.subject_mastery(cards),
                         [("Maths", 50, 2), ("Bio", 50, 1), ("General", 0, 1)])

    def test_limit_and_empty(self):
        self.assertEqual(stats.subject_mastery([]), [])
        cards = [{"subject": s} for s in "abcde"]
        self.assertEqual(len(stats.subject_mastery(cards, limit=3)), 3)


class TopicTests(unittest.TestCase):
    CARDS = [{"subject": "Physics", "topic": "Ohm's law", "box": 5, "due": "2026-11-20"},
             {"subject": "Physics", "topic": "ohm's law", "box": 3, "due": "2026-11-01"},
             {"subject": "Maths", "topic": "Fractions", "box": 5},
             {"subject": "Maths", "box": 1}]

    def test_topic_mastery_groups_case_insensitively(self):
        self.assertEqual(stats.topic_mastery(self.CARDS),
                         [("Physics", "Ohm's law", 75, 2), ("Maths", "Fractions", 100, 1)])

    def test_topics_mastered(self):
        self.assertEqual(stats.topics_mastered(self.CARDS), 1)
        self.assertEqual(stats.topics_mastered(self.CARDS, threshold=70), 2)

    def test_remember_topic_moves_to_front_without_duplicates(self):
        recent = stats.remember_topic([], "Maths", "Fractions", "t1")
        recent = stats.remember_topic(recent, "Physics", "Ohm's law", "t2")
        recent = stats.remember_topic(recent, "Maths", "fractions", "t3")
        self.assertEqual([r["topic"] for r in recent], ["fractions", "Ohm's law"])
        self.assertEqual(stats.remember_topic(recent, "Maths", "  ", "t4"), recent)
        many = []
        for i in range(20):
            many = stats.remember_topic(many, "S", f"t{i}", i)
        self.assertEqual(len(many), 12)

    def test_focus_skips_mastered_topics(self):
        data = {"flashcards": self.CARDS,
                "recent_topics": [{"subject": "Maths", "topic": "Fractions"},
                                  {"subject": "Physics", "topic": "Ohm's law"}]}
        focus = stats.todays_focus(data, TODAY)
        self.assertEqual((focus["topic"], focus["percent"], focus["cards"], focus["due"]), ("Ohm's law", 75, 2, 1))

    def test_focus_topic_without_cards(self):
        data = {"flashcards": [], "recent_topics": [{"subject": "Biology", "topic": "Mitosis"}]}
        self.assertEqual(stats.todays_focus(data, TODAY),
                         {"subject": "Biology", "topic": "Mitosis", "percent": None, "cards": 0, "due": 0})

    def test_focus_falls_back_to_weakest_subject(self):
        focus = stats.todays_focus({"flashcards": self.CARDS, "recent_topics": []}, TODAY)
        self.assertEqual((focus["subject"], focus["topic"]), ("Maths", ""))

    def test_no_focus_without_data(self):
        self.assertIsNone(stats.todays_focus({}, TODAY))


if __name__ == "__main__":
    unittest.main()
