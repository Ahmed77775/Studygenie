"""Creating notes, the one path every screen uses to save a note."""

import uuid
from datetime import datetime


class NotesMixin:
    def _next_note_id(self):
        """A collision-safe id. Older notes may still have a numeric timestamp
        id; both kinds coexist since ids are only compared for equality."""
        return uuid.uuid4().hex

    def add_note(self, title, content):
        """Creates a note and saves it straight away. Returns True on success,
        False if there was nothing to save or the write failed (the note is
        then rolled back so memory matches what is on disk)."""
        title = (title or "").strip() or "Untitled note"
        content = (content or "").strip()
        if not content:
            return False
        note_id = self._next_note_id()
        self.data["notes"].append({
            "id": note_id, "title": title, "content": content,
            "created": datetime.now().isoformat(timespec="seconds"), "updated": None,
        })
        if self.save_data():
            self.note_id = note_id
            self.add_xp(2)
            return True
        self.data["notes"] = [n for n in self.data["notes"] if n["id"] != note_id]
        return False
