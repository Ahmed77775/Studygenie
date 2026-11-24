"""AI Teacher: a calm study chat. The conversation scrolls on its own,
the message box stays at the bottom, images can be attached, and any
answer can become a note, flashcards or a quiz."""

import time
from pathlib import Path

import flet as ft

from ..prompts import short_topic

from .. import ai_service
from .. import components as c
from .. import speech
from .. import theme as t
from .learn import prepare_image

MODES = ("Explain simply", "Summarize notes", "Make a study plan", "Practice problem")


class TeacherPage:
    title = "AI Teacher"
    scrolls_itself = True

    def __init__(self, shell):
        self.shell = shell
        self.core = shell.core
        self.subject, self.mode = "General", MODES[0]
        self.messages = []      # {"role": "user"|"assistant", "content": str, "image": bytes|None}
        self.busy = False
        self.error = ""
        self.attachment = None  # (name, jpeg bytes)
        self.draft = ""
        self.picker = None
        self._list = None
        self._live = None
        self._last_push = 0.0

    # ------------------------------- layout --------------------------------

    def build(self, prompt=None, subject=None):
        if subject:
            self.subject = subject
        if prompt and not self.busy:
            self.draft = prompt
        phone = self.shell.layout == "phone"
        self._list = ft.ListView(controls=self._message_controls(), spacing=t.L, auto_scroll=True, expand=True,
                                 padding=ft.Padding.symmetric(vertical=t.L, horizontal=t.XS))
        return ft.Column([
            self._toolbar(phone),
            ft.Container(self._list, expand=True),
            self._composer(phone),
        ], spacing=t.M, expand=True)

    def _toolbar(self, phone):
        clear = c.text_button("New chat", self._clear, icon=ft.Icons.ADD_COMMENT_OUTLINED, color=t.TEXT,
                              disabled=not self.messages or self.busy)
        if phone:
            summary = t.text(f"{self.subject} · {self.core.teaching_language} · {self.mode}", t.BODY, t.MUTED,
                             expand=True, no_wrap=True,
                             overflow=ft.TextOverflow.ELLIPSIS)
            return ft.Row([summary, c.icon_button(ft.Icons.TUNE, lambda _e: self._open_settings(), "Chat settings"),
                           clear], vertical_alignment=ft.CrossAxisAlignment.CENTER)
        return ft.ResponsiveRow([
            ft.Container(c.dropdown("Subject", self.core.SUBJECTS, self.subject, self._set_subject), col={"md": 3}),
            ft.Container(c.language_dropdown(self.core, "Teaching language",
                                             on_change=lambda _v: self.shell.refresh(self)), col={"md": 3}),
            ft.Container(c.dropdown("Mode", MODES, self.mode, self._set("mode")), col={"md": 4}),
            ft.Container(clear, col={"md": 2}, alignment=ft.Alignment.CENTER_RIGHT),
        ], spacing=t.S, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def _open_settings(self):
        sheet = ft.BottomSheet(ft.Container(ft.Column([
            t.text("Chat settings", t.SUBTITLE, weight=t.SEMIBOLD),
            c.dropdown("Subject", self.core.SUBJECTS, self.subject, self._set_subject),
            c.language_dropdown(self.core, "Teaching language"),
            c.dropdown("Mode", MODES, self.mode, self._set("mode")),
            c.primary_button("Done", lambda _e: self.shell.page.pop_dialog(), expand=True),
        ], spacing=t.M, tight=True), padding=t.XL), bgcolor=t.DIALOG, show_drag_handle=True,
            on_dismiss=lambda _e: self.shell.refresh(self))
        self.shell.page.show_dialog(sheet)

    def _set(self, field):
        return lambda e: setattr(self, field, e.control.value)

    def _set_subject(self, e):
        self.subject = e.control.value
        if not self.messages:
            self.shell.refresh(self)  # suggested prompts follow the subject

    def _message_controls(self):
        if not self.messages:
            prompts = self.core.SUBJECT_PROMPTS.get(self.subject, self.core.SUBJECT_PROMPTS["General"])
            return [ft.Container(ft.Column([
                ft.Icon(ft.Icons.CHAT_BUBBLE_OUTLINE, size=32, color=t.MUTED),
                t.text("What are you working on?", t.TITLE, weight=t.SEMIBOLD),
                t.text("Ask a question, paste your notes, or attach a photo of a problem.", t.BODY, t.MUTED,
                       text_align=ft.TextAlign.CENTER),
                ft.Row([c.chip(p, False, lambda _e, q=p: self._use_prompt(q)) for p in prompts],
                       wrap=True, spacing=t.S, run_spacing=t.S, alignment=ft.MainAxisAlignment.CENTER),
            ], spacing=t.M, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.Padding.only(top=t.XXL), alignment=ft.Alignment.CENTER)]
        controls = [self._bubble(m, i) for i, m in enumerate(self.messages)]
        if self.error:
            controls.append(c.error_message(self.error, on_retry=lambda _e: self._retry()))
        return controls

    def _bubble(self, message, index):
        mine = message["role"] == "user"
        parts = []
        if message.get("image"):
            parts.append(ft.Image(message["image"], height=160, fit=ft.BoxFit.CONTAIN, border_radius=10,
                                  semantics_label="Attached photo"))
        if mine:
            parts.append(t.text(message["content"], t.BODY, selectable=True))
        else:
            body = c.markdown(message["content"] or "")
            if index == len(self.messages) - 1 and self.busy:
                self._live = body
                if not message["content"]:
                    parts.append(c.loading("Genie is thinking…"))
            parts.append(body)
        bubble = ft.Container(
            ft.Column(parts, spacing=t.S, tight=True),
            bgcolor=t.ELEVATED if mine else t.SURFACE_GLASS,
            border=None if mine else ft.Border.all(1, t.BORDER),
            border_radius=ft.BorderRadius.only(top_left=t.RADIUS, top_right=t.RADIUS,
                                               bottom_left=t.RADIUS if mine else 4, bottom_right=4 if mine else t.RADIUS),
            padding=ft.Padding.symmetric(horizontal=t.L, vertical=t.M),
        )
        column = [ft.Row([ft.Container(bubble, expand=8), ft.Container(expand=2)] if not mine else
                         [ft.Container(expand=2), ft.Container(bubble, expand=8)])]
        is_last_answer = not mine and index == len(self.messages) - 1 and not self.busy and message["content"]
        if is_last_answer:
            column.append(ft.Row(wrap=True, spacing=t.XS, controls=[
                c.text_button("Save to Notes", lambda _e: self._save_note(message["content"]), icon=ft.Icons.BOOKMARK_ADD_OUTLINED),
                c.text_button("Make flashcards", lambda _e: self._generate("flashcards", message["content"]),
                              icon=ft.Icons.STYLE_OUTLINED),
                c.text_button("Quiz me", lambda _e: self._generate("quiz", message["content"]), icon=ft.Icons.QUIZ_OUTLINED),
                *self._voice_buttons(message["content"]),
            ]))
        return ft.Column(column, spacing=t.XS)

    def _composer(self, phone):
        self._field = c.text_field(hint="Ask StudyGenie…", multiline=True, min_lines=1, max_lines=6,
                                   value=self.draft, expand=True, autofocus=not phone)
        self._field.on_submit = lambda _e: self.send()
        self._field.on_change = lambda e: setattr(self, "draft", e.control.value)
        attachment = []
        if self.attachment:
            attachment.append(ft.Row([
                ft.Icon(ft.Icons.IMAGE_OUTLINED, size=18, color=t.MUTED),
                t.text(self.attachment[0], t.CAPTION, t.TEXT, expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                c.icon_button(ft.Icons.CLOSE, lambda _e: self._remove_attachment(), "Remove image", size=18),
            ], spacing=t.S))
        send = ft.IconButton(
            icon=ft.Icons.ARROW_UPWARD, on_click=lambda _e: self.send(), tooltip="Send (Enter)",
            disabled=self.busy, icon_size=t.ICON,
            style=ft.ButtonStyle(
                bgcolor={ft.ControlState.DISABLED: t.TRACK, ft.ControlState.HOVERED: t.ACCENT_HOVER,
                         ft.ControlState.DEFAULT: t.ACCENT},
                color={ft.ControlState.DISABLED: t.DISABLED_TEXT, ft.ControlState.DEFAULT: t.BG},
                side={ft.ControlState.FOCUSED: ft.BorderSide(2, t.TEXT),  # light ring: the button itself is teal
                      ft.ControlState.DEFAULT: ft.BorderSide(0, ft.Colors.TRANSPARENT)},
                shape=ft.RoundedRectangleBorder(radius=12)))
        row = ft.Row([c.icon_button(ft.Icons.ATTACH_FILE, self._attach, "Attach an image"), self._field, send],
                     vertical_alignment=ft.CrossAxisAlignment.END, spacing=t.S)
        hint = [] if phone else [t.text("Enter to send · Shift+Enter for a new line", t.CAPTION, t.MUTED)]
        return ft.Column([*attachment, row, *hint], spacing=t.XS)

    # ------------------------------- actions --------------------------------

    def _use_prompt(self, prompt):
        self.draft = prompt
        self.send()

    async def _attach(self, _e=None):
        if self.picker is None:
            self.picker = ft.FilePicker()
            self.shell.page.services.append(self.picker)
            self.shell.page.update()
        files = await self.picker.pick_files(dialog_title="Attach an image",
                                             file_type=ft.FilePickerFileType.IMAGE, with_data=True)
        if not files:
            return
        chosen = files[0]
        try:
            raw = chosen.bytes if chosen.bytes else Path(chosen.path).read_bytes()
            self.attachment = (chosen.name, prepare_image(raw))
        except Exception:
            self.shell.toast("That file couldn't be opened as an image.")
            return
        self.shell.refresh(self)

    def _remove_attachment(self):
        self.attachment = None
        self.shell.refresh(self)

    def send(self):
        question = (self.draft or "").strip()
        if self.busy or not question:
            return
        image = self.attachment[1] if self.attachment else None
        history = [{"role": m["role"], "content": m["content"]} for m in self.messages if m["content"]]
        self.messages.append({"role": "user", "content": question, "image": image})
        self.messages.append({"role": "assistant", "content": ""})
        self.draft, self.attachment, self.error, self.busy = "", None, "", True
        self.core.count_question(self.subject)
        self.shell.refresh(self)
        self._ask(question, history, image)

    def _ask(self, question, history, image):
        def piece(text):
            self.messages[-1]["content"] += text
            now = time.monotonic()
            if now - self._last_push > 0.08:  # ~12 redraws a second is smooth and cheap
                self._last_push = now
                self._push_live()

        def done(answer):
            self.messages[-1]["content"] = answer
            self.busy = False
            self.core.finish_answer()
            self.shell.refresh(self)

        def failed(message):
            self.messages.pop()  # drop the empty answer bubble
            self.busy, self.error = False, message
            self.shell.refresh(self)

        ai_service.ask(question, history, self.subject, self.core.teaching_language, self.mode, image,
                       on_piece=piece, on_done=done, on_error=failed)

    def _push_live(self):
        if self._live is not None:
            self._live.value = self.messages[-1]["content"]
            try:
                self._live.update()
                if self._list is not None:
                    self._list.scroll_to(offset=-1, duration=0)
            except Exception:
                pass

    def _retry(self):
        last_question = next((m for m in reversed(self.messages) if m["role"] == "user"), None)
        if last_question is None:
            return
        index = self.messages.index(last_question)
        history = [{"role": m["role"], "content": m["content"]} for m in self.messages[:index] if m["content"]]
        self.messages.append({"role": "assistant", "content": ""})
        self.busy, self.error = True, ""
        self.shell.refresh(self)
        self._ask(last_question["content"], history, last_question.get("image"))

    def _voice_buttons(self, answer):
        """Read-aloud uses this computer's voices, so phones on the web
        version don't get it (the sound would come out of the computer)."""
        if not speech.available() or self.shell.page.web:
            return []
        return [c.text_button("Read aloud", lambda _e: speech.speak(answer), icon=ft.Icons.VOLUME_UP_OUTLINED),
                c.icon_button(ft.Icons.STOP_CIRCLE_OUTLINED, lambda _e: speech.stop(), "Stop reading")]

    def on_leave(self):
        speech.stop()

    def _clear(self, _e=None):
        speech.stop()
        self.messages, self.error, self.draft = [], "", ""
        self.shell.refresh(self)

    def _save_note(self, answer):
        question = next((m["content"] for m in reversed(self.messages) if m["role"] == "user"), "AI Teacher")
        title = short_topic(question, 50)
        if self.core.add_note(title, answer):
            self.shell.toast(f"Saved to Notes as “{title}”")
        else:
            self.shell.toast("The note couldn't be saved. Please try again.")

    def _generate(self, kind, answer):
        question = next((m["content"] for m in reversed(self.messages) if m["role"] == "user"), "")
        topic = short_topic(question, 50) or self.subject
        self.shell.toast("Genie is writing your " + ("flashcards…" if kind == "flashcards" else "quiz…"))

        def ready(items):
            if kind == "flashcards":
                self.core.add_generated_cards(items, self.subject, topic)
                self.shell.toast(f"{len(items)} flashcards added for “{topic}”")
            else:
                self.core.start_generated_quiz(self.subject, topic)
                self.shell.page_object("practice").load_quiz(items, self.subject, topic)
                self.shell.navigate("practice")

        ai_service.generate_set(kind, answer, self.subject, self.core.teaching_language, on_done=ready,
                                on_error=lambda message: self.shell.toast(message))
