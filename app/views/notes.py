"""Notes: saved notes on the left, the editor on the right. On phones the
list and the editor are separate screens."""

import flet as ft

from .. import components as c
from .. import pdf
from .. import theme as t


class NotesPage:
    title = "Notes"

    def __init__(self, shell):
        self.shell = shell
        self.core = shell.core
        self.selected = None     # note id, "new", or None
        self.message = ""

    def build(self):
        phone = self.shell.layout == "phone"
        notes = self.core.notes_newest_first()
        if self.selected not in (None, "new") and not any(n["id"] == self.selected for n in notes):
            self.selected = None
        if phone:
            return self._editor(notes) if self.selected else self._list(notes)
        if self.selected is None and notes:
            self.selected = notes[0]["id"]
        return ft.ResponsiveRow([
            ft.Container(self._list(notes), col={"xs": 12, "md": 4}),
            ft.Container(self._editor(notes), col={"xs": 12, "md": 8}),
        ], spacing=t.XL, run_spacing=t.XL)

    def _list(self, notes):
        export = ([c.icon_button(ft.Icons.PICTURE_AS_PDF_OUTLINED, self._export, "Export all notes as a PDF")]
                  if notes and pdf.available() else [])
        header = ft.Row([t.text("Notes", t.TITLE, weight=t.SEMIBOLD, expand=True), *export,
                         c.secondary_button("New note", lambda _e: self._open("new"), icon=ft.Icons.ADD)],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER)
        if not notes:
            return c.panel(ft.Column([header, c.empty_state(
                ft.Icons.STICKY_NOTE_2_OUTLINED, "No notes yet",
                "Write one here, or save an answer from AI Teacher or Photo Study.")], spacing=t.L))
        rows = []
        for note in notes:
            preview = " ".join(note["content"].split())[:90]
            rows.append(c.row_button(ft.Column([
                t.text(note["title"] or "Untitled note", t.BODY, weight=t.SEMIBOLD, no_wrap=True,
                       overflow=ft.TextOverflow.ELLIPSIS),
                t.text(preview, t.CAPTION, t.MUTED, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                t.text(self.core._note_time_label(note.get("updated") or note.get("created")), t.CAPTION, t.MUTED),
            ], spacing=2), lambda _e, i=note["id"]: self._open(i), selected=note["id"] == self.selected,
                padding=ft.Padding.all(t.M)))
        return c.panel(ft.Column([header, ft.Column(rows, spacing=t.XS)], spacing=t.L), padding=t.L)

    def _editor(self, notes):
        note = next((n for n in notes if n["id"] == self.selected), None)
        title = c.text_field("Title", value=note["title"] if note else "")
        body = c.text_field("Note", multiline=True, min_lines=12, max_lines=30, value=note["content"] if note else "")
        message = ft.Container(c.error_message(self.message) if self.message else None)

        def save(_e=None):
            try:
                if note is None:
                    if not self.core.add_note(title.value, body.value):
                        raise ValueError("Write something before saving the note.")
                    self.selected = self.core.data["notes"][-1]["id"]
                else:
                    self.core.update_note(note["id"], title.value, body.value)
            except (ValueError, OSError) as exc:
                self.message = str(exc)
                self.shell.refresh(self)
                return
            self.message = ""
            self.shell.refresh(self)
            self.shell.toast("Note saved")

        def delete(_e=None):
            def remove():
                try:
                    self.core.delete_note(note["id"])
                except OSError as exc:
                    self.shell.toast(str(exc))
                    return
                self.selected = None
                self.shell.refresh(self)
                self.shell.toast("Note deleted")
            self.shell.confirm("Delete this note?", "This can't be undone.", "Delete", remove)

        top = []
        if self.shell.layout == "phone":
            top.append(c.text_button("All notes", lambda _e: self._open(None), icon=ft.Icons.ARROW_BACK, color=t.TEXT))
        actions = ft.Row([
            *([c.text_button("Delete", delete, icon=ft.Icons.DELETE_OUTLINE, color=t.MUTED)] if note else []),
            ft.Container(expand=True),
            c.primary_button("Save note", save, icon=ft.Icons.CHECK),
        ])
        if not note and self.selected != "new":
            return c.panel(c.empty_state(ft.Icons.EDIT_NOTE, "Pick a note", "Choose a note, or start a new one.",
                                         c.secondary_button("New note", lambda _e: self._open("new"))))
        return c.panel(ft.Column([*top, title, body, message, actions], spacing=t.M,
                                 horizontal_alignment=ft.CrossAxisAlignment.STRETCH))

    async def _export(self, _e=None):
        notes = self.core.notes_newest_first()
        try:
            data = pdf.notes(notes, self.core._note_time_label)
        except Exception:
            self.shell.toast("The PDF couldn't be made. Please try again.")
            return
        if await self.shell.save_file(data, "studygenie_notes.pdf", "Your notes PDF"):
            self.core.made_pdf(4)

    def _open(self, note_id):
        self.selected, self.message = note_id, ""
        self.shell.refresh(self)
