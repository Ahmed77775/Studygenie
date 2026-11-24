import unittest
from datetime import date, timedelta

from app.scheduling import SchedulingMixin
from tests.helpers import AppTestCase

TODAY = date(2026, 11, 8)


class CardIsDueTests(unittest.TestCase):
    def test_new_card_is_due(self):
        self.assertTrue(SchedulingMixin.card_is_due({}, TODAY))

    def test_past_and_today_are_due(self):
        self.assertTrue(SchedulingMixin.card_is_due({"due": "2026-11-01"}, TODAY))
        self.assertTrue(SchedulingMixin.card_is_due({"due": "2026-11-08"}, TODAY))

    def test_future_is_not_due(self):
        self.assertFalse(SchedulingMixin.card_is_due({"due": "2026-11-09"}, TODAY))

    def test_unreadable_date_counts_as_due(self):
        self.assertTrue(SchedulingMixin.card_is_due({"due": "next tuesday"}, TODAY))


class ScheduleCardTests(unittest.TestCase):
    def test_knew_it_moves_up_one_box(self):
        card = {"box": 1}
        SchedulingMixin.schedule_card(card, True, TODAY)
        self.assertEqual(card["box"], 2)
        self.assertEqual(card["due"], (TODAY + timedelta(days=2)).isoformat())

    def test_each_box_uses_its_interval(self):
        for start, days in ((1, 2), (2, 4), (3, 8), (4, 16)):
            card = {"box": start}
            SchedulingMixin.schedule_card(card, True, TODAY)
            self.assertEqual(card["due"], (TODAY + timedelta(days=days)).isoformat(), start)

    def test_box_is_capped_at_five(self):
        card = {"box": 5}
        SchedulingMixin.schedule_card(card, True, TODAY)
        self.assertEqual(card["box"], 5)
        self.assertEqual(card["due"], (TODAY + timedelta(days=16)).isoformat())

    def test_missed_it_goes_back_to_box_one_due_today(self):
        card = {"box": 4, "due": "2026-12-01"}
        SchedulingMixin.schedule_card(card, False, TODAY)
        self.assertEqual(card["box"], 1)
        self.assertEqual(card["due"], TODAY.isoformat())

    def test_missing_box_is_treated_as_box_one(self):
        card = {"box": None}
        SchedulingMixin.schedule_card(card, True, TODAY)
        self.assertEqual(card["box"], 2)


class DueCardOrderTests(AppTestCase, unittest.TestCase):
    def test_only_due_cards_lowest_box_first(self):
        future = (date.today() + timedelta(days=5)).isoformat()
        self.app.data["flashcards"] = [
            {"question": "a", "answer": "1", "box": 3, "due": None},
            {"question": "b", "answer": "2", "box": 1, "due": future},  # not due
            {"question": "c", "answer": "3", "box": 1, "due": None},
        ]
        self.assertEqual(self.app.due_card_indices(), [2, 0])

    def test_just_rated_card_goes_to_the_back(self):
        cards = [{"question": q, "answer": q, "box": 1, "due": None} for q in "abc"]
        self.app.data["flashcards"] = cards
        self.app._review_counter = 1
        self.app._review_order[id(cards[0])] = 1  # card "a" was just missed
        self.assertEqual(self.app.due_card_indices(), [1, 2, 0])


if __name__ == "__main__":
    unittest.main()
