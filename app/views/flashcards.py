"""Flashcards: review what's due (Leitner spaced repetition), browse the
whole deck, add cards or have Genie write them."""

import flet as ft

from ..prompts import short_topic

from .. import ai_service
from .. import components as c
from .. import theme as t


class FlashcardsPage:
    title = "Flashcards"

    def __init__(self, shell):
        self.shell = shell
        self.core = shell.core
        self.mode = "review"     # "review" (due cards) or "browse" (every card)
        self.topic = None        # optional filter
        self.subject = None      # optional filter
        self.revealed = False
        self.browse_index = 0
        self.generating = False

    # ------------------------------- layout --------------------------------

    def build(self, topic=None, subject=None):
        if topic is not None or subject is not None:
            self.topic, self.subject, self.mode, self.revealed = topic or None, subject, "review", False
        cards = self._filtered(self.core.data["flashcards"])
        due = self._filtered(self.core.due_cards())
        header = ft.Column([
            ft.Row([ft.Column([t.text("Flashcards", t.DISPLAY, weight=t.SEMIBOLD),
                               t.text("Recall first, then check. Cards you miss come back sooner.", t.SUBTITLE, t.MUTED)],
                              spacing=t.XS, expand=True)],
                   vertical_alignment=ft.CrossAxisAlignment.END),
            ft.Row([
                c.chip(f"Due today · {len(due)}", self.mode == "review", lambda _e: self._set_mode("review")),
                c.chip(f"All cards · {len(cards)}", self.mode == "browse", lambda _e: self._set_mode("browse")),
                *([self._filter_chip()] if self.topic or self.subject else []),
            ], wrap=True, spacing=t.S, run_spacing=t.S),
        ], spacing=t.L)
        tools = ft.Row([
            c.secondary_button("Add a card", lambda _e: self._add_dialog(), icon=ft.Icons.ADD),
            c.secondary_button("Generate with AI", lambda _e: self._generate_dialog(), icon=ft.Icons.AUTO_AWESOME_OUTLINED,
                               disabled=self.generating),
            *([c.loading("Writing flashcards…")] if self.generating else []),
        ], wrap=True, spacing=t.S, run_spacing=t.S)

        if not self.core.data["flashcards"]:
            body = c.panel(c.empty_state(
                ft.Icons.STYLE_OUTLINED, "Your deck is empty",
                "Add a card yourself, or let Genie write a set on any topic.",
                c.primary_button("Generate with AI", lambda _e: self._generate_dialog())))
        elif self.mode == "review":
            body = self._review(due)
        else:
            body = self._browse(cards)
        side = self._boxes(cards)
        grid = ft.ResponsiveRow([ft.Container(body, col={"xs": 12, "lg": 8}),
                                 ft.Container(side, col={"xs": 12, "lg": 4})], spacing=t.XL, run_spacing=t.XL)
        return ft.Column([header, tools, grid], spacing=t.L)

    def _filter_chip(self):
        label = f"Topic: {self.topic}" if self.topic else f"Subject: {self.subject}"
        return c.chip(label, True, lambda _e: self._clear_filter(), icon=ft.Icons.CLOSE)

    def _filtered(self, cards):
        if self.topic:
            return [x for x in cards if (x.get("topic") or "").lower() == self.topic.lower()]
        if self.subject:
            return [x for x in cards if (x.get("subject") or "General") == self.subject]
        return cards

    def _card_face(self, card, footer):
        side = "Answer" if self.revealed else "Question"
        text = card["answer"] if self.revealed else card["question"]
        meta = " · ".join(filter(None, [card.get("subject") or "General", card.get("topic"),
                                        f"Box {int(card.get('box') or 1)} of {self.MAX_BOX}"]))
        return c.panel(ft.Column([
            ft.Row([t.text(side.upper(), t.CAPTION, t.TEXT, t.SEMIBOLD), ft.Container(expand=True),
                    t.text(meta, t.CAPTION, t.TEXT, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS)]),
            ft.Container(t.text(text, t.TITLE + 2, weight=t.SEMIBOLD if not self.revealed else t.REGULAR,
                                text_align=ft.TextAlign.CENTER, selectable=True),
                         alignment=ft.Alignment.CENTER, padding=ft.Padding.symmetric(vertical=t.XXL), expand=False),
            footer,
        ], spacing=t.L), elevated=True, radius=t.RADIUS_LARGE, padding=t.XL)

    MAX_BOX = 5

    # ------------------------------- review ---------------------------------

    def _review(self, due):
        if not due:
            return c.panel(c.empty_state(
                ft.Icons.TASK_ALT, "All caught up",
                "No cards are due right now. Reviewed cards come back on their own schedule.",
                c.secondary_button("Browse all cards", lambda _e: self._set_mode("browse"))))
        card = due[0]
        if not self.revealed:
            footer = ft.Row([c.primary_button("Show answer", lambda _e: self._reveal(), icon=ft.Icons.VISIBILITY_OUTLINED)],
                            alignment=ft.MainAxisAlignment.CENTER)
        else:
            footer = ft.Row([
                c.secondary_button("Missed it", lambda _e: self._rate(card, False), icon=ft.Icons.REPLAY, expand=True),
                c.primary_button("Got it", lambda _e: self._rate(card, True), icon=ft.Icons.CHECK, expand=True),
            ], spacing=t.M)
        remaining = t.text(f"{len(due)} card{'s' if len(due) != 1 else ''} left today", t.BODY, t.MUTED)
        return ft.Column([self._card_face(card, footer), remaining], spacing=t.M)

    def _reveal(self):
        self.revealed = True
        self.core.reveal_card()
        self.shell.refresh(self)

    def _rate(self, card, knew_it):
        self.core.rate_card(card, knew_it)
        self.revealed = False
        self.shell.refresh(self)

    # ------------------------------- browse ---------------------------------

    def _browse(self, cards):
        if not cards:
            return c.panel(c.empty_state(ft.Icons.FILTER_ALT_OFF_OUTLINED, "No cards match",
                                         "Clear the filter to see your whole deck.",
                                         c.secondary_button("Clear filter", lambda _e: self._clear_filter())))
        self.browse_index %= len(cards)
        card = cards[self.browse_index]
        footer = ft.Row([
            c.icon_button(ft.Icons.CHEVRON_LEFT, lambda _e: self._step(-1), "Previous card"),
            ft.Container(expand=True),
            c.secondary_button("Hide answer" if self.revealed else "Show answer", lambda _e: self._flip()),
            ft.Container(expand=True),
            c.icon_button(ft.Icons.CHEVRON_RIGHT, lambda _e: self._step(1), "Next card"),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
        info = ft.Row([t.text(f"Card {self.browse_index + 1} of {len(cards)}", t.BODY, t.MUTED, expand=True),
                       c.text_button("Delete card", lambda _e: self._delete(card), icon=ft.Icons.DELETE_OUTLINE,
                                     color=t.MUTED)])
        return ft.Column([self._card_face(card, footer), info], spacing=t.M)

    def _flip(self):
        self.revealed = not self.revealed
        self.shell.refresh(self)

    def _step(self, delta):
        self.browse_index += delta
        self.revealed = False
        self.shell.refresh(self)

    def _delete(self, card):
        def remove():
            self.core.delete_card(card)
            self.revealed = False
            self.shell.refresh(self)
            self.shell.toast("Card deleted")
        self.shell.confirm("Delete this card?", "It will be removed from your deck.", "Delete", remove)

    # ------------------------------- side -----------------------------------

    def _boxes(self, cards):
        counts = {box: 0 for box in range(1, self.MAX_BOX + 1)}
        for card in cards:
            counts[min(max(int(card.get("box") or 1), 1), self.MAX_BOX)] += 1
        largest = max(counts.values()) or 1
        rows = []
        for box, count in counts.items():
            label = "Mastered" if box == self.MAX_BOX else f"Box {box}"
            rows.append(ft.Row([t.text(label, t.BODY, t.MUTED, width=80),
                                c.progress_bar(count / largest, height=8, expand=True),
                                t.text(str(count), t.BODY, weight=t.SEMIBOLD, width=32, text_align=ft.TextAlign.RIGHT)],
                               spacing=t.M))
        return c.panel(ft.Column([c.section_header("Deck progress", subtitle="Correct answers move a card up a box"),
                                  *rows], spacing=t.M))

    # ------------------------------- modes ----------------------------------

    def _set_mode(self, mode):
        self.mode, self.revealed = mode, False
        self.shell.refresh(self)

    def _clear_filter(self):
        self.topic = self.subject = None
        self.revealed = False
        self.shell.refresh(self)

    # ------------------------------- dialogs --------------------------------

    def _add_dialog(self):
        page = self.shell.page
        question = c.text_field("Question", multiline=True, min_lines=2, max_lines=4, autofocus=True)
        answer = c.text_field("Answer", multiline=True, min_lines=2, max_lines=6)
        state = {"subject": self.subject or "General"}
        topic = c.text_field("Topic (optional)", value=self.topic or "")
        message = ft.Container()

        def save(_e=None):
            try:
                self.core.add_card(question.value, answer.value, state["subject"], topic.value)
            except ValueError as exc:
                message.content = c.error_message(str(exc))
                message.update()
                return
            page.pop_dialog()
            self.shell.refresh(self)
            self.shell.toast("Card added")

        page.show_dialog(ft.AlertDialog(
            title=t.text("Add a card", t.TITLE, weight=t.SEMIBOLD),
            content=ft.Column([question, answer,
                               c.dropdown("Subject", self.core.SUBJECTS, state["subject"],
                                          lambda e: state.update(subject=e.control.value)),
                               topic, message], spacing=t.M, tight=True, width=440, scroll=ft.ScrollMode.AUTO),
            actions=[c.text_button("Cancel", lambda _e: page.pop_dialog(), color=t.TEXT), c.primary_button("Save card", save)],
            bgcolor=t.DIALOG, shape=ft.RoundedRectangleBorder(radius=t.RADIUS_LARGE)))

    def _generate_dialog(self):
        page = self.shell.page
        topic = c.text_field("Topic", "e.g. Ohm's law, photosynthesis, World War I causes", value=self.topic or "",
                             autofocus=True)
        state = {"subject": self.subject or "General"}
        message = ft.Container()

        def generate(_e=None):
            text = (topic.value or "").strip()
            if not text:
                message.content = c.error_message("Add a topic so Genie knows what to write about.")
                message.update()
                return
            page.pop_dialog()
            self._generate(text, state["subject"], self.core.teaching_language)

        topic.on_submit = generate
        page.show_dialog(ft.AlertDialog(
            title=t.text("Generate flashcards", t.TITLE, weight=t.SEMIBOLD),
            content=ft.Column([t.text("Genie writes six short, exam-ready cards.", t.BODY, t.MUTED), topic,
                               c.dropdown("Subject", self.core.SUBJECTS, state["subject"],
                                          lambda e: state.update(subject=e.control.value)),
                               c.language_dropdown(self.core),
                               message], spacing=t.M, tight=True, width=440),
            actions=[c.text_button("Cancel", lambda _e: page.pop_dialog(), color=t.TEXT),
                     c.primary_button("Generate", generate)],
            bgcolor=t.DIALOG, shape=ft.RoundedRectangleBorder(radius=t.RADIUS_LARGE)))

    def _generate(self, topic_text, subject, language):
        self.generating = True
        self.shell.refresh(self)
        topic = short_topic(topic_text)

        def ready(items):
            self.generating = False
            self.core.add_generated_cards(items, subject, topic)
            self.topic, self.subject, self.mode, self.revealed = topic, None, "review", False
            self.shell.refresh(self)
            self.shell.toast(f"{len(items)} flashcards added for “{topic}”")

        def failed(message):
            self.generating = False
            self.shell.refresh(self)
            self.shell.toast(message)

        ai_service.generate_set("flashcards", topic_text, subject, language, on_done=ready, on_error=failed)
