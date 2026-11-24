"""Learn: Photo Study as a step-by-step flow.

1. Choose an image (a camera photo on phones, a file on computers).
2. See the preview and the topic Genie detected.
3. Explain it, turn it into notes, or generate a quiz from it.
"""

import io
from pathlib import Path

import flet as ft

from ..deps import Image
from ..prompts import short_topic, split_topic_line

from .. import ai_service
from .. import components as c
from .. import theme as t

MAX_SIDE = 1280  # downscale large phone photos: faster for the model, same detail
ACTIONS = (("explain", "Explain", ft.Icons.LIGHTBULB_OUTLINE),
           ("notes", "Create notes", ft.Icons.NOTES),
           ("quiz", "Generate quiz", ft.Icons.QUIZ_OUTLINED))


class LearnPage:
    title = "Learn"

    def __init__(self, shell):
        self.shell = shell
        self.core = shell.core
        self.picker = None
        self.image = None          # prepared JPEG bytes
        self.image_name = ""
        self.subject = "General"
        self.topic = ""
        self.result = ""           # the latest answer, without its topic line
        self.result_mode = ""
        self.busy = ""             # "", "reading", "quiz"
        self.error = ""
        self._live = None          # the Markdown control being streamed into

    # ------------------------------- layout --------------------------------

    def build(self):
        if self.image is None:
            return ft.Column([self._intro(), self._upload_area()], spacing=t.XL)
        preview = c.panel(self._photo_panel(), padding=t.L, col={"xs": 12, "md": 5})
        work = ft.Container(self._work_panel(), col={"xs": 12, "md": 7})
        return ft.Column([self._intro(), ft.ResponsiveRow([preview, work], spacing=t.XL, run_spacing=t.XL)],
                         spacing=t.XL)

    def _intro(self):
        return ft.Column([t.text("Photo Study", t.DISPLAY, weight=t.SEMIBOLD),
                          t.text("Photograph a textbook page or a question and study it step by step.",
                                 t.SUBTITLE, t.MUTED)], spacing=t.XS)

    def _upload_area(self):
        phone = self.shell.layout == "phone"
        inner = ft.Column([
            ft.Icon(ft.Icons.ADD_PHOTO_ALTERNATE_OUTLINED, size=40, color=t.ACCENT),
            t.text("Take a photo or choose an image" if phone else "Choose an image to study",
                   t.SUBTITLE, weight=t.SEMIBOLD, text_align=ft.TextAlign.CENTER),
            t.text("A clear photo of one question or one section works best. JPG or PNG.",
                   t.BODY, t.MUTED, text_align=ft.TextAlign.CENTER),
        ], spacing=t.S, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        area = ft.Button(
            content=ft.Container(inner, padding=ft.Padding.symmetric(vertical=t.XXL + 16, horizontal=t.XL)),
            on_click=self.pick_image, tooltip="Choose an image",
            style=ft.ButtonStyle(
                bgcolor={ft.ControlState.HOVERED: t.ELEVATED, ft.ControlState.DEFAULT: t.SURFACE_GLASS},
                overlay_color={ft.ControlState.PRESSED: t.PRESSED, ft.ControlState.DEFAULT: ft.Colors.TRANSPARENT},
                side={ft.ControlState.FOCUSED: ft.BorderSide(2, t.FOCUS_RING),
                      ft.ControlState.HOVERED: ft.BorderSide(1, t.ACCENT),
                      ft.ControlState.DEFAULT: ft.BorderSide(1, t.BORDER_STRONG)},
                shape=ft.RoundedRectangleBorder(radius=t.RADIUS_LARGE), elevation=0),
        )
        return ft.Column([area, *([c.error_message(self.error)] if self.error else [])],
                         spacing=t.M, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def _photo_panel(self):
        topic_line = (ft.Row([ft.Icon(ft.Icons.LABEL_OUTLINE, size=t.ICON, color=t.MUTED),
                              ft.Column([t.text("Detected topic", t.CAPTION, t.MUTED),
                                         t.text(self.topic, t.BODY, weight=t.SEMIBOLD)], spacing=0, expand=True)],
                             spacing=t.S)
                      if self.topic else
                      t.text("Reading the photo…" if self.busy == "reading" else "Topic not detected yet",
                             t.BODY, t.MUTED))
        return ft.Column([
            ft.Container(ft.Image(self.image, fit=ft.BoxFit.CONTAIN, border_radius=t.RADIUS - 4,
                                  semantics_label="Your photo"),
                         height=260, alignment=ft.Alignment.CENTER, bgcolor=t.BG,
                         border_radius=t.RADIUS - 4),
            topic_line,
            ft.Row([c.dropdown("Subject", self.core.SUBJECTS, self.subject, self._set_subject, expand=True),
                    c.language_dropdown(self.core, on_change=lambda _v: self.shell.refresh(self), expand=True)],
                   spacing=t.S),
            *([note] if (note := c.language_note(self.core)) else []),
            ft.Row([c.text_button("Choose another image", self.pick_image, icon=ft.Icons.SWAP_HORIZ, color=t.TEXT)]),
        ], spacing=t.M)

    def _work_panel(self):
        busy = bool(self.busy)
        actions = ft.Row(wrap=True, spacing=t.S, run_spacing=t.S, controls=[
            (c.primary_button if key == "explain" and not self.result else c.secondary_button)(
                label, lambda _e, k=key: self.run(k), icon=icon, disabled=busy)
            for key, label, icon in ACTIONS])
        parts = [t.text("What would you like to do?", t.SUBTITLE, weight=t.SEMIBOLD), actions]
        if self.error:
            parts.append(c.error_message(self.error, on_retry=lambda _e: self.run(self.result_mode or "explain")))
        if self.busy == "quiz":
            parts.append(c.loading("Writing your quiz…"))
        if self.busy == "reading" or self.result:
            self._live = c.markdown(self.result or "")
            heading = {"explain": "Explanation", "notes": "Notes"}.get(self.result_mode, "Answer")
            result_box = ft.Container(
                ft.Column([self._live], scroll=ft.ScrollMode.AUTO),
                padding=t.L, bgcolor=t.BG, border_radius=t.RADIUS,
                height=None if self.shell.layout == "phone" else 360)
            parts += [divider_row(heading, c.loading("Genie is reading your photo…") if self.busy == "reading" else None),
                      result_box]
            if self.result and not busy:
                parts.append(ft.Row(wrap=True, spacing=t.S, run_spacing=t.S, controls=[
                    c.secondary_button("Save to Notes", self.save_note, icon=ft.Icons.BOOKMARK_ADD_OUTLINED),
                    c.secondary_button("Make flashcards", self.make_flashcards, icon=ft.Icons.STYLE_OUTLINED),
                ]))
        return c.panel(ft.Column(parts, spacing=t.L), padding=t.XL)

    # -------------------------------- image --------------------------------

    async def pick_image(self, _e=None):
        if self.picker is None:
            self.picker = ft.FilePicker()
            self.shell.page.services.append(self.picker)
            self.shell.page.update()
        files = await self.picker.pick_files(dialog_title="Choose a photo to study",
                                             file_type=ft.FilePickerFileType.IMAGE, with_data=True)
        if not files:
            return
        chosen = files[0]
        try:
            raw = chosen.bytes if chosen.bytes else Path(chosen.path).read_bytes()
            self.image = prepare_image(raw)
        except Exception:
            self.error = "That file couldn't be opened as an image. Try a JPG or PNG."
            self.image = None
            self.shell.refresh(self)
            return
        self.image_name = chosen.name
        self.topic, self.result, self.result_mode, self.error = "", "", "", ""
        self.run("explain")  # reading it straight away gives the preview its detected topic

    def _set_subject(self, e):
        self.subject = e.control.value

    # -------------------------------- Genie ---------------------------------

    def run(self, action):
        if self.busy or self.image is None:
            return
        if action == "quiz":
            self.make_quiz()
            return
        self.busy, self.error, self.result_mode, self.result = "reading", "", action, ""
        self.shell.refresh(self)

        def streamed(text_so_far):
            if "\n" not in text_so_far and text_so_far.lstrip("* ").lower().startswith("topic"):
                return  # the topic line is still being written
            self.result = split_topic_line(text_so_far)[1]
            self._push_live()

        def done(topic, body):
            self.busy = ""
            self.result = body
            if topic:
                self.topic = topic
            self.core.finish_photo(self.subject, self.topic)
            self.shell.refresh(self)

        def failed(message):
            self.busy, self.error = "", message
            self.shell.refresh(self)

        ai_service.read_photo(self.image, action, self.subject, self.core.teaching_language,
                              on_piece=streamed, on_done=done, on_error=failed)

    def _push_live(self):
        if self._live is not None:
            self._live.value = self.result
            try:
                self._live.update()
            except Exception:
                pass  # the learner moved to another page; the result is kept for later

    def make_quiz(self):
        """A quiz from what Genie read on the page (reading it first if needed)."""
        source = self.result

        def generate(text):
            self.busy, self.error = "quiz", ""
            self.shell.refresh(self)
            topic = self.topic or short_topic(text)

            def ready(items):
                self.busy = ""
                self.core.start_generated_quiz(self.subject, topic)
                self.shell.page_object("practice").load_quiz(items, self.subject, topic)
                self.shell.navigate("practice")

            def failed(message):
                self.busy, self.error = "", message
                self.shell.refresh(self)

            ai_service.generate_set("quiz", text, self.subject, self.core.teaching_language, on_done=ready, on_error=failed)

        if source:
            generate(source)
            return
        self.busy, self.result_mode = "reading", "explain"
        self.shell.refresh(self)
        ai_service.read_photo(self.image, "explain", self.subject, self.core.teaching_language,
                              on_done=lambda topic, body: (setattr(self, "topic", topic or self.topic),
                                                           setattr(self, "result", body), generate(body)),
                              on_error=lambda m: (setattr(self, "busy", ""), setattr(self, "error", m),
                                                  self.shell.refresh(self)))

    def save_note(self, _e=None):
        kind = "Notes" if self.result_mode == "notes" else "Photo study"
        title = f"{kind}: {self.topic or self.subject}"
        if self.core.add_note(title, self.result):
            self.shell.toast(f"Saved to Notes as “{title}”")
        else:
            self.shell.toast("The note couldn't be saved. Please try again.")

    def make_flashcards(self, _e=None):
        self.busy = "quiz"
        self.shell.refresh(self)
        topic = self.topic or short_topic(self.result)

        def ready(items):
            self.busy = ""
            self.core.add_generated_cards(items, self.subject, topic)
            self.shell.refresh(self)
            self.shell.toast(f"{len(items)} flashcards added for “{topic}”")

        def failed(message):
            self.busy, self.error = "", message
            self.shell.refresh(self)

        ai_service.generate_set("flashcards", self.result, self.subject, self.core.teaching_language, on_done=ready, on_error=failed)


def divider_row(label, trailing=None):
    controls = [t.text(label, t.SUBTITLE, weight=t.SEMIBOLD, expand=True)]
    if trailing:
        controls.append(trailing)
    return ft.Row(controls, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def prepare_image(raw):
    """Downscales big photos to a JPEG the model reads quickly. Without
    Pillow the original bytes are used as they are."""
    if Image is None:
        return raw
    image = Image.open(io.BytesIO(raw)).convert("RGB")
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=90)
    return buffer.getvalue()
