"""Practice: generate a quiz on any topic, answer it one question at a
time, and review the results. Scores feed the quiz history, streak
and XP."""

import flet as ft

from .. import ai_service
from .. import components as c
from .. import theme as t

LETTERS = "ABCD"


class PracticePage:
    title = "Practice"

    def __init__(self, shell):
        self.shell = shell
        self.core = shell.core
        self.topic = ""
        self.subject = "General"
        self.generating = False
        self.error = ""
        self._reset_quiz()

    def _reset_quiz(self):
        self.questions = []
        self.index = 0
        self.choices = {}      # question index -> chosen option
        self.checked = set()   # question indexes whose answer was checked
        self.score = None      # final percentage once finished

    # ------------------------------ entry ----------------------------------

    def load_quiz(self, items, subject, topic):
        """Starts a quiz made elsewhere (Photo Study, AI Teacher)."""
        self._reset_quiz()
        self.questions, self.subject, self.topic = items, subject, topic

    def build(self, topic=None, subject=None):
        if topic is not None and not self.questions:
            self.topic = topic
        if subject:
            self.subject = subject
        if self.questions and self.score is not None:
            return self._results()
        if self.questions:
            return self._question()
        return self._setup()

    # ------------------------------ set-up ----------------------------------

    def _setup(self):
        topic = c.text_field("Topic", "e.g. Current electricity, fractions, the French Revolution",
                             value=self.topic, on_submit=lambda _e: start(None))

        def start(_e):
            self.topic = (topic.value or "").strip()
            self.generate()

        form = c.panel(ft.Column([
            t.text("Create a quiz", t.TITLE, weight=t.SEMIBOLD),
            t.text("Five multiple-choice questions, written by Genie for your topic.", t.BODY, t.MUTED),
            topic,
            ft.ResponsiveRow([
                ft.Container(c.dropdown("Subject", self.core.SUBJECTS, self.subject, self._set("subject")),
                             col={"xs": 12, "sm": 6}),
                ft.Container(c.language_dropdown(self.core, on_change=lambda _v: self.shell.refresh(self)),
                             col={"xs": 12, "sm": 6}),
            ], spacing=t.S, run_spacing=t.S),
            *([note] if (note := c.language_note(self.core)) else []),
            *([c.error_message(self.error, on_retry=start)] if self.error else []),
            c.loading("Writing your quiz… this can take a little while.") if self.generating else
            ft.Row([c.primary_button("Generate quiz", start, icon=ft.Icons.AUTO_AWESOME_OUTLINED)]),
        ], spacing=t.L), col={"xs": 12, "lg": 7})
        return ft.Column([
            ft.Column([t.text("Practice", t.DISPLAY, weight=t.SEMIBOLD),
                       t.text("Test yourself, then review what you missed.", t.SUBTITLE, t.MUTED)], spacing=t.XS),
            ft.ResponsiveRow([form, ft.Container(self._history(), col={"xs": 12, "lg": 5})],
                             spacing=t.XL, run_spacing=t.XL),
        ], spacing=t.XL)

    def _history(self):
        scores = self.core.data.get("quiz_scores", [])[-8:]
        if not scores:
            body = c.empty_state(ft.Icons.QUERY_STATS, "No quizzes yet", "Your recent scores will show here.")
        else:
            average = round(sum(scores) / len(scores))
            body = ft.Column([
                c.section_header("Recent scores", subtitle=f"Average {average}% over your last {len(scores)}"),
                c.bar_chart(scores, [str(i + 1) for i in range(len(scores))], highlight=len(scores) - 1,
                            height=150, value_suffix="%"),
            ], spacing=t.L)
        due = len(self.core.due_cards())
        actions = [c.text_button(f"Review {due} due flashcard{'s' if due != 1 else ''}",
                                 lambda _e: self.shell.navigate("flashcards"), icon=ft.Icons.STYLE_OUTLINED)] if due else []
        return c.panel(ft.Column([body, *actions], spacing=t.M))

    def _set(self, field):
        return lambda e: setattr(self, field, e.control.value)

    def generate(self):
        if self.generating:
            return
        if not self.topic:
            self.error = "Add a topic so Genie knows what to ask about."
            self.shell.refresh(self)
            return
        self.generating, self.error = True, ""
        self.shell.refresh(self)

        def ready(items):
            self.generating = False
            self.core.start_generated_quiz(self.subject, self.topic)
            self.load_quiz(items, self.subject, self.topic)
            self.shell.refresh(self)

        def failed(message):
            self.generating, self.error = False, message
            self.shell.refresh(self)

        ai_service.generate_set("quiz", f"Topic: {self.topic}", self.subject, self.core.teaching_language,
                                on_done=ready, on_error=failed)

    # ----------------------------- question ---------------------------------

    def _question(self):
        item = self.questions[self.index]
        total = len(self.questions)
        checked = self.index in self.checked
        chosen = self.choices.get(self.index)
        options = [self._option(LETTERS[i % 4], option, chosen, item["answer"], checked)
                   for i, option in enumerate(item["options"])]
        feedback = []
        if checked:
            right = chosen == item["answer"]
            feedback.append(ft.Container(ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE if right else ft.Icons.CANCEL_OUTLINED, color=t.ACCENT if right else t.ERROR),
                ft.Column([t.text("Correct" if right else f"Not quite — the answer is {item['answer']}",
                                  t.BODY, weight=t.SEMIBOLD),
                           *([t.text(item["explanation"], t.BODY, t.MUTED)] if item.get("explanation") else [])],
                          spacing=t.XS, expand=True)], spacing=t.M, vertical_alignment=ft.CrossAxisAlignment.START),
                padding=t.L, border_radius=t.RADIUS, bgcolor=t.BG))
        last = self.index == total - 1
        if not checked:
            main_action = c.primary_button("Check answer", self._check, disabled=chosen is None)
        else:
            main_action = c.primary_button("See results" if last else "Next question", self._next,
                                           icon=None if last else ft.Icons.ARROW_FORWARD)
        nav = ft.Row([
            c.secondary_button("Back", lambda _e: self._go(self.index - 1), icon=ft.Icons.ARROW_BACK,
                               disabled=self.index == 0),
            ft.Container(expand=True),
            main_action,
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
        header = ft.Column([
            ft.Row([t.text(self.topic or "Quiz", t.BODY, t.MUTED, expand=True, no_wrap=True,
                           overflow=ft.TextOverflow.ELLIPSIS),
                    t.text(f"Question {self.index + 1} of {total}", t.BODY, weight=t.SEMIBOLD)]),
            c.progress_bar((self.index + (1 if checked else 0)) / total),
        ], spacing=t.S)
        card = c.panel(ft.Column([
            t.text(item["question"], t.TITLE, weight=t.SEMIBOLD, selectable=True),
            ft.Column(options, spacing=t.S),
            *feedback,
        ], spacing=t.L), padding=t.XL)
        quit_row = ft.Row([c.text_button("Quit quiz", self._quit, color=t.MUTED)], alignment=ft.MainAxisAlignment.END)
        return ft.Column([header, card, nav, quit_row], spacing=t.L)

    def _option(self, letter, option, chosen, answer, checked):
        is_chosen = option == chosen
        if checked and option == answer:
            icon, color, note = ft.Icons.CHECK_CIRCLE, t.ACCENT, "Correct answer"
        elif checked and is_chosen:
            icon, color, note = ft.Icons.CANCEL_OUTLINED, t.ERROR, "Your answer"
        elif is_chosen:
            icon, color, note = ft.Icons.RADIO_BUTTON_CHECKED, t.TEXT, "Selected"
        else:
            icon, color, note = ft.Icons.RADIO_BUTTON_UNCHECKED, t.MUTED, ""
        content = ft.Row([
            ft.Container(t.text(letter, t.CAPTION, t.TEXT, t.SEMIBOLD), width=28, height=28, border_radius=8,
                         bgcolor=t.ELEVATED if is_chosen else t.TRACK, alignment=ft.Alignment.CENTER),
            t.text(option, t.BODY, expand=True),
            *([t.text(note, t.CAPTION, t.MUTED)] if note and checked else []),
            ft.Icon(icon, size=t.ICON, color=color),
        ], spacing=t.M)
        return ft.Container(
            c.row_button(content, None if checked else (lambda _e, o=option: self._choose(o)),
                         selected=is_chosen, padding=ft.Padding.symmetric(horizontal=t.M, vertical=t.M)),
            border=ft.Border.all(1, t.BORDER_STRONG if not is_chosen else t.ACCENT), border_radius=12)

    def _choose(self, option):
        self.choices[self.index] = option
        self.shell.refresh(self)

    def _check(self, _e=None):
        if self.index in self.choices:
            self.checked.add(self.index)
            self.shell.refresh(self)

    def _go(self, index):
        if 0 <= index < len(self.questions):
            self.index = index
            self.shell.refresh(self)

    def _next(self, _e=None):
        if self.index < len(self.questions) - 1:
            self._go(self.index + 1)
            return
        correct = sum(1 for i, q in enumerate(self.questions) if self.choices.get(i) == q["answer"])
        self.score = self.core.finish_quiz(correct, len(self.questions))
        self.shell.refresh(self)

    def _quit(self, _e=None):
        def leave():
            self._reset_quiz()
            self.shell.refresh(self)
        self.shell.confirm("Quit this quiz?", "Your answers so far won't be saved.", "Quit quiz", leave)

    # ------------------------------ results ----------------------------------

    def _results(self):
        total = len(self.questions)
        correct = sum(1 for i, q in enumerate(self.questions) if self.choices.get(i) == q["answer"])
        review = []
        for i, q in enumerate(self.questions):
            right = self.choices.get(i) == q["answer"]
            review.append(ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE if right else ft.Icons.CANCEL_OUTLINED, size=t.ICON,
                        color=t.ACCENT if right else t.ERROR),
                ft.Column([t.text(q["question"], t.BODY, weight=t.SEMIBOLD),
                           t.text(("Correct: " if right else f"You answered {self.choices.get(i) or '—'} · Answer: ")
                                  + q["answer"], t.CAPTION, t.MUTED)], spacing=2, expand=True),
            ], spacing=t.M, vertical_alignment=ft.CrossAxisAlignment.START))

        def new_quiz(_e):
            self._reset_quiz()
            self.shell.refresh(self)

        summary = c.panel(ft.Column([
            t.text("Quiz complete", t.CAPTION, t.TEXT, t.SEMIBOLD),
            t.text(f"{self.score}%", t.DISPLAY + 8, weight=t.SEMIBOLD),
            t.text(f"{correct} of {total} correct · {self.topic}", t.BODY, t.TEXT),
            ft.Row([c.primary_button("New quiz", new_quiz),
                    c.secondary_button("Dashboard", lambda _e: self.shell.navigate("dashboard"))],
                   wrap=True, spacing=t.S, run_spacing=t.S),
        ], spacing=t.M), elevated=True, radius=t.RADIUS_LARGE)
        return ft.Column([summary, c.panel(ft.Column([t.text("Review", t.SUBTITLE, weight=t.SEMIBOLD), *review],
                                                     spacing=t.L))], spacing=t.XL)
