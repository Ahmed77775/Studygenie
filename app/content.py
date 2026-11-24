"""Static study content: subjects, languages, quick prompts and badges."""

from . import prompts


class ContentMixin:
    """Static study content: subjects, languages, quick prompts and badges."""

    SUBJECTS = ("General", "Mathematics", "Physics", "Chemistry", "Biology",
                "Computer Science", "English", "History", "Economics")

    SUBJECT_ICONS = {
        "General": "✦", "Mathematics": "∑", "Physics": "⚛", "Chemistry": "⚗",
        "Biology": "🧬", "Computer Science": "💻", "English": "📖",
        "History": "🏛", "Economics": "📈",
    }

    # Glyphs used for the ambient floating-symbol animation. Mixed math,
    # physics, chemistry and biology motifs so the effect reads as "science
    # come alive" rather than one subject in particular.
    FLOATING_GLYPHS = ("∑", "π", "√", "∞", "⚛", "⚗", "🧬", "∆", "∫", "ƒ(x)",
                        "α", "β", "θ", "≈", "e=mc²", "H₂O", "±", "Ω")

    LANGUAGES = ("English", "Hindi", "Telugu", "Urdu", "Tamil", "Kannada",
                 "Malayalam", "Bengali", "Marathi")

    # The AI teaching language: one saved preference that every screen starts
    # from. (The interface itself is English; that's a separate setting.)

    @property
    def teaching_language(self):
        language = (getattr(self, "data", None) or {}).get("teaching_language") or "English"
        return language if language in self.LANGUAGES else "English"

    def save_teaching_language(self, language_or_label):
        language = prompts.language_from_label(language_or_label)
        if language in self.LANGUAGES and language != self.data.get("teaching_language"):
            self.data["teaching_language"] = language
            self.save_data()

    def language_choices(self):
        return [prompts.language_label(language) for language in self.LANGUAGES]

    SUBJECT_PROMPTS = {
        "General": ("Explain this topic simply", "Make a 5-day study plan",
                    "Summarize my notes", "Quiz me on this"),
        "Mathematics": ("Solve this step by step", "Explain this formula",
                         "Give me a practice problem", "Where is this used in real life?"),
        "Physics": ("Explain this with an analogy", "Walk through this numerical",
                    "What's the real-world use?", "Give me a practice problem"),
        "Chemistry": ("Explain this reaction", "Help me balance this equation",
                      "What's the real-world use?", "Give me a practice problem"),
        "Biology": ("Explain this process step by step", "Give me a mnemonic to remember this",
                    "Compare these two terms", "Quiz me on this"),
        "Computer Science": ("Explain this with code", "Trace through this algorithm",
                             "What's a real-world use case?", "Give me a practice problem"),
        "English": ("Help me analyze this passage", "Improve this paragraph",
                    "Explain this literary device", "Give me essay structure tips"),
        "History": ("Explain the causes and effects", "Summarize this event's timeline",
                    "Compare two perspectives", "Quiz me on key dates"),
        "Economics": ("Explain this with an example", "Walk through this graph",
                      "What's the real-world impact?", "Give me a practice problem"),
    }

    BADGES = (
        {"id": "first_session", "name": "First Focus", "icon": "🌱",
         "desc": "Complete your first focus session.",
         "check": lambda d: d["sessions"] >= 1},
        {"id": "streak_3", "name": "3-Day Streak", "icon": "🔥",
         "desc": "Study three days in a row.",
         "check": lambda d: d["streak_days"] >= 3},
        {"id": "streak_7", "name": "Week Warrior", "icon": "⚡",
         "desc": "Study seven days in a row.",
         "check": lambda d: d["streak_days"] >= 7},
        {"id": "cards_50", "name": "Card Master", "icon": "▣",
         "desc": "Review 50 flashcards.",
         "check": lambda d: d["flashcards_reviewed"] >= 50},
        {"id": "quiz_5", "name": "Quiz Regular", "icon": "?",
         "desc": "Complete 5 quizzes.",
         "check": lambda d: d["quizzes_taken"] >= 5},
        {"id": "quiz_ace", "name": "Quiz Ace", "icon": "★",
         "desc": "Score 90% or higher on a quiz.",
         "check": lambda d: any(s >= 90 for s in d["quiz_scores"])},
        {"id": "level_5", "name": "Rising Scholar", "icon": "🎓",
         "desc": "Reach level 5.",
         "check": lambda d: d["level"] >= 5},
        {"id": "level_10", "name": "Grandmaster", "icon": "👑",
         "desc": "Reach level 10.",
         "check": lambda d: d["level"] >= 10},
        {"id": "streak_30", "name": "Unstoppable", "icon": "🌟",
         "desc": "Study thirty days in a row.",
         "check": lambda d: d["streak_days"] >= 30},
        {"id": "note_taker", "name": "Note Taker", "icon": "▤",
         "desc": "Save 5 notes.",
         "check": lambda d: len(d.get("notes", [])) >= 5},
        {"id": "note_keeper", "name": "Note Keeper", "icon": "📚",
         "desc": "Save 20 notes.",
         "check": lambda d: len(d.get("notes", [])) >= 20},
        {"id": "curious_mind", "name": "Curious Mind", "icon": "💡",
         "desc": "Ask Genie 20 questions.",
         "check": lambda d: d.get("questions_asked", 0) >= 20},
        {"id": "deep_thinker", "name": "Deep Thinker", "icon": "🔍",
         "desc": "Ask Genie 100 questions.",
         "check": lambda d: d.get("questions_asked", 0) >= 100},
        {"id": "subject_explorer", "name": "Subject Explorer", "icon": "🧭",
         "desc": "Study 3 different subjects.",
         "check": lambda d: len(d.get("subjects_used", [])) >= 3},
        {"id": "all_rounder", "name": "All-Rounder", "icon": "🌐",
         "desc": "Study every subject at least once.",
         "check": lambda d: len(d.get("subjects_used", [])) >= 9},
        {"id": "deck_builder", "name": "Deck Builder", "icon": "🗂",
         "desc": "Generate 5 AI study sets.",
         "check": lambda d: d.get("decks_generated", 0) >= 5},
        {"id": "flawless", "name": "Flawless", "icon": "💯",
         "desc": "Score a perfect 100% on a quiz.",
         "check": lambda d: any(s >= 100 for s in d["quiz_scores"])},
        {"id": "marathoner", "name": "Marathoner", "icon": "🏅",
         "desc": "Rack up 500 total study minutes.",
         "check": lambda d: d.get("study_minutes", 0) >= 500},
        {"id": "pdf_author", "name": "Published", "icon": "📄",
         "desc": "Export your first PDF with PDF Maker.",
         "check": lambda d: d.get("pdfs_created", 0) >= 1},
    )
