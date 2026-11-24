"""Flashcard spaced repetition (Leitner boxes).

Every card sits in box 1-5. "Got it" moves it up one box and pushes its
next review further out; "Missed it" drops it back to box 1, due again today."""

from datetime import date, timedelta


class SchedulingMixin:
    LEITNER_INTERVALS = {1: 1, 2: 2, 3: 4, 4: 8, 5: 16}  # box -> days until next review
    MAX_BOX = 5

    @staticmethod
    def card_is_due(card, today=None):
        due = card.get("due")
        if not due:
            return True  # brand-new cards are always due
        try:
            return date.fromisoformat(due) <= (today or date.today())
        except ValueError:
            return True

    @classmethod
    def schedule_card(cls, card, knew_it, today=None):
        """Moves a card between Leitner boxes and sets its next due date."""
        today = today or date.today()
        box = int(card.get("box") or 1)
        if knew_it:
            box = min(box + 1, cls.MAX_BOX)
            card["due"] = (today + timedelta(days=cls.LEITNER_INTERVALS[box])).isoformat()
        else:
            box = 1
            card["due"] = today.isoformat()
        card["box"] = box

    def due_card_indices(self):
        """Indices of cards due today. Cards not yet rated this session come
        first (lowest box first); a card you just missed goes to the back."""
        cards = self.data["flashcards"]
        due = [i for i, card in enumerate(cards) if self.card_is_due(card)]
        due.sort(key=lambda i: (self._review_order.get(id(cards[i]), -1), int(cards[i].get("box") or 1)))
        return due
