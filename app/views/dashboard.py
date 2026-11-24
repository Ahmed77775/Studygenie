"""Dashboard: Today's Focus first, then the learner's real numbers,
subject progress and the three most useful next actions."""

from datetime import datetime

import flet as ft

from .. import components as c
from .. import theme as t


class DashboardPage:
    title = "Dashboard"

    def __init__(self, shell):
        self.shell = shell
        self.core = shell.core

    def build(self):
        phone = self.shell.layout == "phone"
        main_column = ft.Column([self._focus(), self._continue_learning()], spacing=t.XL)
        side_column = ft.Column([self._stats(), self._today(), self._quick_actions(phone)], spacing=t.XL)
        grid = ft.ResponsiveRow([
            ft.Container(main_column, col={"xs": 12, "lg": 8}),
            ft.Container(side_column, col={"xs": 12, "lg": 4}),
        ], spacing=t.XL, run_spacing=t.XL)
        return ft.Column([self._welcome(), grid], spacing=t.XL)

    # ------------------------------ sections -------------------------------

    def _welcome(self):
        hour = datetime.now().hour
        part = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"
        return ft.Column([
            t.text(f"Good {part}, {self.core.display_name}", t.DISPLAY, weight=t.SEMIBOLD),
            t.text("Your next step is closer than you think.", t.SUBTITLE, t.MUTED),
        ], spacing=t.XS)

    def _focus(self):
        focus = self.core.focus()
        if focus is None:
            body = ft.Column([
                t.text("TODAY'S FOCUS", t.CAPTION, t.TEXT, t.SEMIBOLD),
                t.text("Nothing in progress yet", t.TITLE, weight=t.SEMIBOLD),
                t.text("Scan a page or make flashcards on a topic, and it will appear here so you can pick up "
                       "where you left off.", t.BODY, t.TEXT),
                ft.Row([c.primary_button("Start learning", lambda _e: self.shell.navigate("learn"),
                                         icon=ft.Icons.ARROW_FORWARD)]),
            ], spacing=t.M)
            return c.panel(body, elevated=True, radius=t.RADIUS_LARGE, padding=t.XL + 4)

        topic = focus["topic"] or f"{focus['subject']} flashcards"
        lines = [
            t.text("TODAY'S FOCUS", t.CAPTION, t.TEXT, t.SEMIBOLD),
            ft.Row([ft.Icon(c.subject_icon(focus["subject"]), size=t.ICON, color=t.TEXT),
                    t.text(focus["subject"], t.BODY, t.TEXT)], spacing=t.S),
            t.text(topic, t.DISPLAY, weight=t.SEMIBOLD),
        ]
        if focus["percent"] is None:
            lines.append(t.text("Not practised yet", t.BODY, t.TEXT))
        else:
            due = focus["due"]
            detail = f"{focus['percent']}% complete" + (f"  ·  {due} card{'s' if due != 1 else ''} due" if due else "")
            lines += [t.text(detail, t.BODY, t.TEXT, t.SEMIBOLD),
                      c.progress_bar(focus["percent"] / 100, height=8, color=t.ACCENT)]
        lines.append(ft.Row([c.primary_button("Continue learning", lambda _e: self._continue(focus),
                                              icon=ft.Icons.ARROW_FORWARD)],
                            wrap=True, spacing=t.S, run_spacing=t.S))
        return c.panel(ft.Column(lines, spacing=t.M), elevated=True, radius=t.RADIUS_LARGE, padding=t.XL + 4)

    def _continue(self, focus):
        """Review cards that are due; otherwise practise; with no cards yet, learn it with the AI Teacher."""
        topic = focus["topic"]
        if focus["due"]:
            self.shell.navigate("flashcards", topic=topic, subject=None if topic else focus["subject"])
        elif focus["cards"]:
            self.shell.navigate("practice", topic=topic or focus["subject"], subject=focus["subject"])
        else:
            self.shell.navigate("teacher", prompt=f"Teach me {topic}, step by step.", subject=focus["subject"])

    def _stats(self):
        streak = self.core.data.get("streak_days", 0)
        info = self.core.level_info()

        def figure(icon, value, label):
            return ft.Column([ft.Icon(icon, size=t.ICON, color=t.MUTED),
                              t.text(value, t.TITLE + 2, weight=t.SEMIBOLD),
                              t.text(label, t.CAPTION, t.MUTED)], spacing=t.XS, expand=True)

        return c.panel(ft.Row([
            figure(ft.Icons.LOCAL_FIRE_DEPARTMENT_OUTLINED, f"{streak} day{'s' if streak != 1 else ''}", "Learning streak"),
            figure(ft.Icons.BOLT, f"{info['total']:,}", "Total XP"),
            figure(ft.Icons.WORKSPACE_PREMIUM_OUTLINED, str(self.core.topics_mastered()), "Topics mastered"),
        ], spacing=t.M, vertical_alignment=ft.CrossAxisAlignment.START), padding=t.L + 4)

    def _today(self):
        rows = []
        quests = self.core.daily_quests()
        for label, done, target in quests:
            finished = done >= target
            rows.append(ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE if finished else ft.Icons.RADIO_BUTTON_UNCHECKED, size=t.ICON,
                        color=t.ACCENT if finished else t.MUTED),
                t.text(label, t.BODY, t.MUTED if finished else t.TEXT, expand=True),
                t.text(f"{done}/{target}", t.CAPTION, t.MUTED),
            ], spacing=t.M))
        complete = sum(1 for _, d, tg in quests if d >= tg)
        return c.panel(ft.Column([
            c.section_header("Today", subtitle=f"{complete} of {len(quests)} goals done"),
            *rows,
        ], spacing=t.M), padding=t.L + 4)

    def _quick_actions(self, phone):
        actions = (("Scan a question", ft.Icons.DOCUMENT_SCANNER_OUTLINED, "learn"),
                   ("Ask AI", ft.Icons.CHAT_BUBBLE_OUTLINE, "teacher"),
                   ("Practice now", ft.Icons.QUIZ_OUTLINED, "practice"))
        buttons = [c.secondary_button(label, lambda _e, k=key: self.shell.navigate(k), icon=icon, expand=True)
                   for label, icon, key in actions]
        return ft.Column([t.text("Quick actions", t.SUBTITLE, weight=t.SEMIBOLD), *buttons], spacing=t.S,
                         horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def _continue_learning(self):
        subjects = self.core.subject_progress()
        header = c.section_header("Continue learning", subtitle="Progress comes from your flashcard reviews")
        if not subjects:
            return ft.Column([header, c.panel(c.empty_state(
                ft.Icons.AUTO_STORIES_OUTLINED, "No subjects yet",
                "Make flashcards for a topic and its progress will be tracked here.",
                c.secondary_button("Make flashcards", lambda _e: self.shell.navigate("flashcards"))))],
                spacing=t.M)
        tiles = []
        for subject, percent, cards in subjects:
            tile = c.row_button(ft.Column([
                ft.Row([ft.Icon(c.subject_icon(subject), size=t.ICON, color=t.MUTED),
                        t.text(subject, t.BODY, weight=t.SEMIBOLD, expand=True, no_wrap=True,
                               overflow=ft.TextOverflow.ELLIPSIS),
                        t.text(f"{percent}%", t.BODY, t.TEXT, t.SEMIBOLD)], spacing=t.S),
                c.progress_bar(percent / 100),
                t.text(f"{cards} card{'s' if cards != 1 else ''}", t.CAPTION, t.MUTED),
            ], spacing=t.S), lambda _e, s=subject: self.shell.navigate("flashcards", subject=s),
                padding=ft.Padding.all(t.L), tooltip=f"Review {subject}")
            tiles.append(ft.Container(
                tile, col={"xs": 12, "sm": 6, "xl": 4}, bgcolor=t.SURFACE_GLASS, border_radius=t.RADIUS,
                border=ft.Border.all(1, t.BORDER)))
        return ft.Column([header, ft.ResponsiveRow(tiles, spacing=t.M, run_spacing=t.M)], spacing=t.M)
