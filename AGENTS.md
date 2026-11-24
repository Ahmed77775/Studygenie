# StudyGenie Agent Notes

## Stack
- Python 3.15 with pinned packages in `requirements.txt`.
- Flet 1.1.2 provides the desktop and web UI.
- `app/deps.py` treats Ollama, Pillow, FPDF, and pyttsx3 as optional imports.
- AI prompts use the local Ollama model `gemma3:4b` (`app/prompts.py`).
- Study data is stored in SQLite beside `studygenie.py`; legacy JSON can be imported.

## Entry points and module map
- `studygenie.py` — desktop launcher and `--web` browser server.
- `app/main.py` — Flet page setup, shared data core, sign-in and app shell.
- `app/core.py` — study rules and actions composed from data/feature mixins.
- `app/db.py` — SQLite schema, migrations, load, save, and legacy JSON import.
- `app/config.py` — local data, legacy JSON, and icon paths.
- `app/deps.py` — optional third-party package imports.
- `app/ai_service.py` — threaded Ollama chat, photo, flashcard, and quiz requests.
- `app/prompts.py` — model prompts, response cleanup, and generated-set validation.
- `app/content.py` — static study content, subjects, languages, prompts, and badges.
- `app/login.py` — local profile creation and optional PIN sign-in UI.
- `app/profile.py` — avatars and local PIN hashing.
- `app/components.py` — reusable Flet controls.
- `app/shell.py` — responsive navigation frame and screen container.
- `app/theme.py` — shared colors, spacing, typography, and responsive theme.
- `app/focus_timer.py` — Pomodoro focus timer UI.
- `app/notebook.py` — saved-note operations.
- `app/pdf.py` — PDF exports returned as bytes.
- `app/progress.py` — study minutes, XP, levels, streaks, and badges.
- `app/scheduling.py` — Leitner spaced-repetition rules for flashcards.
- `app/stats.py` — calculations for study statistics.
- `app/speech.py` — desktop read-aloud using pyttsx3.
- `app/views/__init__.py` — shared view-page interface.
- `app/views/dashboard.py` — dashboard screen.
- `app/views/flashcards.py` — flashcard review and deck screen.
- `app/views/learn.py` — photo-study screen.
- `app/views/notes.py` — notes screen.
- `app/views/pdf_maker.py` — PDF document builder screen.
- `app/views/practice.py` — quiz and practice screen.
- `app/views/progress.py` — progress and achievements screen.
- `app/views/sketchpad.py` — drawing and diagram screen.
- `app/views/teacher.py` — AI Teacher chat screen.

## Commands
- Run desktop app: `python studygenie.py`.
- Run browser app locally: `python studygenie.py --web --port 8550`.
- Run tests: `python -m unittest discover -s tests -v`.

## Data and tests
- Tests use temporary SQLite paths from `tests/helpers.py` or test-local temp directories.
- Do not use a personal `studygenie_data.db` or legacy JSON file in tests.
- `.gitignore` excludes the local database, JSON data, and backups.
