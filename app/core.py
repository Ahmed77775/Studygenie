"""StudyGenie's data and rules, without any window.

Combines the logic mixins (storage, XP, levels, streaks, badges,
flashcard scheduling, notes). Each action a screen can take is one
method here, so the XP awards and rules live in one place."""

import threading
from datetime import date, datetime
from pathlib import Path

from . import stats
from .config import DB_PATH, LEGACY_JSON_PATH
from .content import ContentMixin
from .db import DataMixin
from .notebook import NotesMixin
from .profile import AVATARS, hash_pin
from .progress import ProgressMixin
from .scheduling import SchedulingMixin


class StudyCore(ContentMixin, DataMixin, ProgressMixin, SchedulingMixin, NotesMixin):
    AVATARS = AVATARS

    def __init__(self, db_path=DB_PATH, legacy_json_path=LEGACY_JSON_PATH):
        self._lock = threading.RLock()  # Flet runs handlers on worker threads
        self._listeners = []
        self._last_db_error = None
        self.db_path = db_path
        self.legacy_json_path = Path(legacy_json_path)
        self.init_db()
        self.data = self.load_data()
        self.profile = self.data.get("profile")
        self.note_id = None
        self._review_order = {}
        self._review_counter = 0

    # ------------------------------ events ---------------------------------
    # The mixins call these hooks; the Flet shell subscribes to redraw.

    def subscribe(self, listener):
        self._listeners.append(listener)

    def _emit(self, kind, **info):
        for listener in list(self._listeners):
            listener(kind, info)

    def refresh_status(self):
        self._emit("status")

    def celebrate(self, title, subtitle):
        self._emit("celebrate", title=title, subtitle=subtitle)

    def after(self, _ms, callback):
        callback()  # ProgressMixin queues extra badge announcements this way

    def save_data(self):
        with self._lock:
            return super().save_data()

    # ------------------------------ profile --------------------------------

    @property
    def has_profile(self):
        return bool(self.data.get("profile"))

    def create_profile(self, name, avatar, pin=""):
        name = (name or "").strip()
        if not name:
            raise ValueError("Add a name so StudyGenie knows who it's helping.")
        pin = (pin or "").strip()
        if pin and not (pin.isdigit() and 4 <= len(pin) <= 6):
            raise ValueError("A PIN needs to be 4 to 6 digits.")
        self.data["profile"] = {"name": name, "avatar": avatar, "pin_hash": hash_pin(pin) if pin else None}
        if not self.save_data():
            raise OSError("Your profile couldn't be saved. Please try again.")
        self.profile = self.data["profile"]

    def pin_matches(self, pin):
        stored = (self.data.get("profile") or {}).get("pin_hash")
        return not stored or hash_pin((pin or "").strip()) == stored

    def sign_in(self):
        self.profile = self.data.get("profile")
        self.update_streak()
        self._emit("status")

    @property
    def display_name(self):
        name = (self.profile or {}).get("name") or ""
        return name if name and name != "Guest" else "Student"

    # ------------------------------ summary --------------------------------

    def level_info(self):
        level, xp = self.data["level"], self.data["xp"]
        return {"level": level, "title": self.level_title(level), "xp": xp,
                "needed": self.xp_for_level(level), "total": self.total_xp()}

    def focus(self):
        return stats.todays_focus(self.data, date.today())

    def topics_mastered(self):
        return stats.topics_mastered(self.data["flashcards"])

    def subject_progress(self, limit=None):
        return stats.subject_mastery(self.data["flashcards"], limit=limit)

    # ------------------------------ topics ---------------------------------

    def remember_topic(self, subject, topic):
        self.data["recent_topics"] = stats.remember_topic(
            self.data.get("recent_topics"), subject, topic, datetime.now().isoformat(timespec="seconds"))
        self.save_data()

    # ----------------------------- flashcards ------------------------------

    def due_cards(self, topic=None):
        cards = self.data["flashcards"]
        if topic:
            cards = [c for c in cards if (c.get("topic") or "").lower() == topic.lower()]
        due = [c for c in cards if self.card_is_due(c)]
        due.sort(key=lambda c: (self._review_order.get(id(c), -1), int(c.get("box") or 1)))
        return due

    def add_card(self, question, answer, subject, topic=""):
        question, answer = (question or "").strip(), (answer or "").strip()
        if not question or not answer:
            raise ValueError("Add both a question and an answer.")
        self.data["flashcards"].append({"question": question, "answer": answer, "subject": subject,
                                        "box": 1, "due": None, "topic": (topic or "").strip()})
        self.save_data()
        self.track_subject(subject)
        self.add_xp(2)

    def add_generated_cards(self, items, subject, topic):
        for item in items:
            item.setdefault("subject", subject or "Generated deck")
            item["topic"] = topic
            item["box"], item["due"] = 1, None
        self.data["flashcards"].extend(items)
        self.data["decks_generated"] = self.data.get("decks_generated", 0) + 1
        self.track_subject(subject)
        self.save_data()
        self.remember_topic(subject, topic)
        self.add_xp(8)

    def reveal_card(self):
        """Seeing an answer counts as reviewing a card."""
        self.data["flashcards_reviewed"] += 1
        self.bump_today("cards")
        self.save_data()
        self.update_streak()
        self.add_xp(3)

    def rate_card(self, card, knew_it):
        self.schedule_card(card, knew_it)
        self._review_counter += 1
        self._review_order[id(card)] = self._review_counter
        self.save_data()

    def delete_card(self, card):
        self.data["flashcards"] = [c for c in self.data["flashcards"] if c is not card]
        self.save_data()

    # -------------------------------- quiz ---------------------------------

    def start_generated_quiz(self, subject, topic):
        self.data["decks_generated"] = self.data.get("decks_generated", 0) + 1
        self.track_subject(subject)
        self.save_data()
        self.remember_topic(subject, topic)
        self.add_xp(8)

    def finish_quiz(self, correct, total):
        score = round(correct / total * 100) if total else 0
        self.data["quizzes_taken"] += 1
        self.bump_today("quizzes")
        self.data["quiz_scores"].append(score)
        self.save_data()
        self.update_streak()
        self.add_xp(20 + score // 5)
        return score

    # ---------------------------- AI Teacher -------------------------------

    def count_question(self, subject):
        self.data["questions_asked"] = self.data.get("questions_asked", 0) + 1
        self.bump_today("questions")
        self.track_subject(subject)
        self.save_data()

    def finish_answer(self):
        self.update_streak()
        self.add_xp(5)

    # ---------------------------- Photo Study ------------------------------

    def finish_photo(self, subject, topic):
        self.bump_today("photos")
        self.track_subject(subject)
        self.save_data()
        if topic:
            self.remember_topic(subject, topic)
        self.add_xp(5)

    # -------------------------------- notes --------------------------------

    def update_note(self, note_id, title, content):
        content = (content or "").strip()
        if not content:
            raise ValueError("Write something before saving the note.")
        for note in self.data["notes"]:
            if note["id"] == note_id:
                previous = dict(note)
                note.update(title=(title or "").strip() or "Untitled note", content=content,
                            updated=datetime.now().isoformat(timespec="seconds"))
                if self.save_data():
                    return
                note.clear()
                note.update(previous)
                raise OSError("The note couldn't be saved. Your text is still here; try again.")
        raise KeyError(note_id)

    def delete_note(self, note_id):
        before = list(self.data["notes"])
        self.data["notes"] = [n for n in before if n["id"] != note_id]
        if not self.save_data():
            self.data["notes"] = before
            raise OSError("The note couldn't be deleted. Please try again.")

    def notes_newest_first(self):
        return sorted(self.data["notes"], key=lambda n: self._parse_note_time(n.get("updated") or n.get("created")),
                      reverse=True)

    # ---------------------------- focus timer ------------------------------

    def finish_focus_session(self, minutes):
        self.data["sessions"] += 1
        self.add_study_minutes(minutes)

    # --------------------------- Sketchpad, PDFs ---------------------------

    def saved_sketch(self):
        self.add_xp(2)

    def made_pdf(self, xp):
        """A PDF Maker document is worth more XP than a quick notes export."""
        self.data["pdfs_created"] = self.data.get("pdfs_created", 0) + 1
        self.save_data()
        self.add_xp(xp)

    def progress_rows(self):
        """The figures in the downloadable progress report."""
        data = self.data
        scores = data["quiz_scores"]
        return (
            ("Student", self.display_name),
            ("Level", f"{data['level']} ({self.level_title(data['level'])})"),
            ("XP", f"{data['xp']} / {self.xp_for_level(data['level'])}"),
            ("Current streak", f"{data.get('streak_days', 0)} days"),
            ("Total study minutes", str(data["study_minutes"])),
            ("Focus sessions completed", str(data["sessions"])),
            ("Flashcards reviewed", str(data["flashcards_reviewed"])),
            ("Quizzes taken", str(data["quizzes_taken"])),
            ("Average quiz score", f"{round(sum(scores) / len(scores)) if scores else 0}%"),
            ("Achievements unlocked", f"{len(data['badges'])} / {len(self.BADGES)}"),
        )
