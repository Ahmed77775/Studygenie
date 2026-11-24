"""Progress: level and XP, streaks, this week's study time, quiz scores,
mastery by subject and topic, and achievements. Real data only."""

from datetime import date, timedelta

import flet as ft

from .. import stats

from .. import components as c
from .. import pdf
from .. import theme as t


class ProgressPage:
    title = "Progress"

    def __init__(self, shell):
        self.shell = shell
        self.core = shell.core

    def build(self):
        data = self.core.data
        summary = stats.summary(data, date.today())
        span = lambda xs, md, xl: {"xs": xs, "md": md, "xl": xl}  # noqa: E731
        return ft.Column([
            ft.Row([ft.Column([t.text("Progress", t.DISPLAY, weight=t.SEMIBOLD),
                               t.text("How your studying is adding up.", t.SUBTITLE, t.MUTED)], spacing=t.XS,
                              expand=True),
                    *([c.secondary_button("Download report", self._download, icon=ft.Icons.DOWNLOAD)]
                      if pdf.available() else [])],
                   wrap=True, vertical_alignment=ft.CrossAxisAlignment.END, run_spacing=t.M),
            ft.ResponsiveRow([
                ft.Container(self._level(), col=span(12, 12, 5)),
                ft.Container(self._figures(summary), col=span(12, 12, 7)),
                ft.Container(self._week(), col=span(12, 6, 6)),
                ft.Container(self._quizzes(), col=span(12, 6, 6)),
                ft.Container(self._subjects(), col=span(12, 6, 6)),
                ft.Container(self._topics(), col=span(12, 6, 6)),
                ft.Container(self._achievements(), col=12),
            ], spacing=t.XL, run_spacing=t.XL),
        ], spacing=t.XL)

    async def _download(self, _e=None):
        try:
            data = pdf.progress_report(self.core.progress_rows())
        except Exception:
            self.shell.toast("The report couldn't be made. Please try again.")
            return
        if await self.shell.save_file(data, "studygenie_progress.pdf", "Your progress report"):
            self.core.made_pdf(4)

    def _level(self):
        info = self.core.level_info()
        return c.panel(ft.Column([
            t.text("LEVEL", t.CAPTION, t.TEXT, t.SEMIBOLD),
            t.text(f"Level {info['level']} — {info['title']}", t.TITLE + 2, weight=t.SEMIBOLD),
            c.progress_bar(info["xp"] / info["needed"], height=8),
            ft.Row([t.text(f"{info['xp']} / {info['needed']} XP", t.BODY, t.TEXT, expand=True),
                    t.text(f"{info['needed'] - info['xp']} XP to level {info['level'] + 1}", t.BODY, t.TEXT)]),
            t.text(f"{info['total']:,} XP earned in total", t.CAPTION, t.TEXT),
        ], spacing=t.M), elevated=True, radius=t.RADIUS_LARGE)

    def _figures(self, s):
        hours, minutes = divmod(s["study_minutes"], 60)
        figures = (
            (ft.Icons.LOCAL_FIRE_DEPARTMENT_OUTLINED, f"{s['current_streak']} days", "Current streak"),
            (ft.Icons.EMOJI_EVENTS_OUTLINED, f"{s['best_streak']} days", "Best streak"),
            (ft.Icons.WORKSPACE_PREMIUM_OUTLINED, str(self.core.topics_mastered()), "Topics mastered"),
            (ft.Icons.SCHEDULE, f"{hours}h {minutes}m" if hours else f"{minutes}m", "Time studied"),
            (ft.Icons.STYLE_OUTLINED, f"{s['due_today']}", "Cards due today"),
            (ft.Icons.QUIZ_OUTLINED, "—" if s["quiz_average"] is None else f"{s['quiz_average']}%", "Quiz average"),
        )
        cells = [ft.Container(ft.Column([ft.Icon(icon, size=t.ICON, color=t.MUTED),
                                         t.text(value, t.TITLE, weight=t.SEMIBOLD),
                                         t.text(label, t.CAPTION, t.MUTED)], spacing=t.XS),
                              col={"xs": 6, "sm": 4}, padding=ft.Padding.symmetric(vertical=t.S))
                 for icon, value, label in figures]
        return c.panel(ft.ResponsiveRow(cells, spacing=t.L, run_spacing=t.M))

    def _week(self):
        today = date.today()
        days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
        minutes = [int(self.core.data["activity"].get(d.isoformat(), 0)) for d in days]
        goal = max(1, int(self.core.data.get("daily_goal", 60)))
        chart = c.bar_chart(minutes, ["Today" if d == today else d.strftime("%a") for d in days],
                            highlight=6, height=170)
        return c.panel(ft.Column([c.section_header("This week", subtitle=f"Minutes of focus · daily goal {goal}m"),
                                  chart], spacing=t.L))

    def _quizzes(self):
        scores = self.core.data.get("quiz_scores", [])[-10:]
        if not scores:
            body = c.empty_state(ft.Icons.QUERY_STATS, "No quizzes yet", "Take one in Practice to see your scores.",
                                 c.secondary_button("Go to Practice", lambda _e: self.shell.navigate("practice")))
            return c.panel(ft.Column([c.section_header("Quiz scores"), body], spacing=t.L))
        chart = c.bar_chart(scores, [str(i + 1) for i in range(len(scores))], highlight=len(scores) - 1,
                            height=170, value_suffix="%")
        return c.panel(ft.Column([c.section_header("Quiz scores", subtitle=f"Your last {len(scores)} quizzes"),
                                  chart], spacing=t.L))

    def _mastery_rows(self, rows):
        return [ft.Column([ft.Row([t.text(label, t.BODY, expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                                   t.text(f"{percent}%", t.BODY, weight=t.SEMIBOLD)]),
                           c.progress_bar(percent / 100)], spacing=t.XS)
                for label, percent in rows]

    def _subjects(self):
        rows = [(s, p) for s, p, _ in self.core.subject_progress()]
        body = self._mastery_rows(rows) or [c.empty_state(ft.Icons.AUTO_STORIES_OUTLINED, "No subjects yet",
                                                          "Subject progress comes from your flashcards.")]
        return c.panel(ft.Column([c.section_header("By subject"), *body], spacing=t.M))

    def _topics(self):
        rows = [(f"{topic} · {subject}", percent) for subject, topic, percent, _ in stats.topic_mastery(self.core.data["flashcards"])[:8]]
        body = self._mastery_rows(rows) or [c.empty_state(ft.Icons.LABEL_OUTLINE, "No topics yet",
                                                          "Topics appear when you make flashcards on one.")]
        return c.panel(ft.Column([c.section_header("By topic", subtitle="80% or more counts as mastered"), *body],
                                 spacing=t.M))

    def _achievements(self):
        unlocked = set(self.core.data["badges"])
        tiles = []
        for badge in self.core.BADGES:
            have = badge["id"] in unlocked
            tiles.append(ft.Container(ft.Row([
                ft.Icon(ft.Icons.WORKSPACE_PREMIUM if have else ft.Icons.LOCK_OUTLINE, size=t.ICON,
                        color=t.ACCENT if have else t.MUTED),
                ft.Column([t.text(badge["name"], t.BODY, t.TEXT if have else t.MUTED, t.SEMIBOLD),
                           t.text(badge["desc"], t.CAPTION, t.MUTED),
                           t.text("Unlocked" if have else "Locked", t.CAPTION, t.TEXT if have else t.MUTED)],
                          spacing=2, expand=True),
            ], spacing=t.M, vertical_alignment=ft.CrossAxisAlignment.START),
                col={"xs": 12, "sm": 6, "xl": 4}, padding=t.M, border_radius=t.RADIUS,
                bgcolor=t.BG if not have else t.ELEVATED, border=ft.Border.all(1, t.BORDER)))
        return c.panel(ft.Column([
            c.section_header("Achievements", subtitle=f"{len(unlocked)} of {len(self.core.BADGES)} unlocked"),
            ft.ResponsiveRow(tiles, spacing=t.M, run_spacing=t.M),
        ], spacing=t.L))
