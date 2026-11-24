"""The focus timer (Pomodoro), reachable from the header on every screen.

Completed focus sessions add study minutes, which feed the daily goal,
the streak and XP."""

import threading
import time

import flet as ft

from . import components as c
from . import theme as t

PRESETS = (("Focus", 25), ("Short break", 5), ("Long break", 15))


class FocusTimer:
    def __init__(self, shell):
        self.shell = shell
        self.mode, self.minutes = PRESETS[0]
        self.remaining = self.minutes * 60
        self.running = False
        self._thread = None
        self._dialog_time = None
        self._dialog_button = None
        self._header_label = None

    # ------------------------------ display --------------------------------

    def clock(self):
        minutes, seconds = divmod(max(0, self.remaining), 60)
        return f"{minutes:02d}:{seconds:02d}"

    def header_button(self, compact=False):
        self._header_label = t.text(self.clock(), t.CAPTION + 1, t.TEXT, t.SEMIBOLD,
                                    visible=self.running or self.remaining != self.minutes * 60)
        return ft.TextButton(
            content=ft.Row([ft.Icon(ft.Icons.TIMER_OUTLINED, size=18, color=t.ACCENT if self.running else t.MUTED),
                            self._header_label], spacing=t.XS + 2, tight=True),
            on_click=lambda _e: self.open(), tooltip="Focus timer",
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=t.RADIUS_PILL),
                padding=ft.Padding.symmetric(horizontal=t.S + 2, vertical=t.XS + 2),
                overlay_color={ft.ControlState.HOVERED: t.HOVER, ft.ControlState.DEFAULT: ft.Colors.TRANSPARENT},
                side={ft.ControlState.FOCUSED: ft.BorderSide(2, t.FOCUS_RING),
                      ft.ControlState.DEFAULT: ft.BorderSide(0, ft.Colors.TRANSPARENT)}),
        )

    def _refresh(self):
        for control, value in ((self._header_label, self.clock()), (self._dialog_time, self.clock())):
            if control is not None:
                control.value = value
                control.visible = True
                try:
                    control.update()
                except Exception:
                    pass
        if self._dialog_button is not None:
            self._dialog_button.content = "Pause" if self.running else "Start"
            try:
                self._dialog_button.update()
            except Exception:
                pass

    # ------------------------------- dialog --------------------------------

    def open(self):
        page = self.shell.page
        self._dialog_time = t.text(self.clock(), 48, t.TEXT, t.SEMIBOLD)
        self._dialog_button = c.primary_button("Pause" if self.running else "Start", lambda _e: self.toggle())

        def choose(mode, minutes):
            self.set_preset(mode, minutes)
            page.pop_dialog()
            self.open()

        presets = ft.Row([c.chip(f"{name} · {mins}m", name == self.mode, lambda _e, n=name, m=mins: choose(n, m))
                          for name, mins in PRESETS], wrap=True, spacing=t.S, run_spacing=t.S)
        page.show_dialog(ft.AlertDialog(
            title=t.text("Focus timer", t.TITLE, weight=t.SEMIBOLD),
            content=ft.Column([
                t.text("Completed focus sessions count toward today's goal and your streak.", t.BODY, t.MUTED),
                presets,
                ft.Container(self._dialog_time, alignment=ft.Alignment.CENTER, padding=t.L),
            ], spacing=t.L, tight=True, width=360),
            actions=[c.text_button("Reset", lambda _e: self.reset(), color=t.TEXT), self._dialog_button],
            bgcolor=t.DIALOG, shape=ft.RoundedRectangleBorder(radius=t.RADIUS_LARGE),
            on_dismiss=lambda _e: self._forget_dialog()))

    def _forget_dialog(self):
        self._dialog_time = self._dialog_button = None

    # ------------------------------- control -------------------------------

    def set_preset(self, mode, minutes):
        self.running = False
        self.mode, self.minutes = mode, minutes
        self.remaining = minutes * 60
        self._refresh()

    def reset(self):
        self.set_preset(self.mode, self.minutes)

    def toggle(self):
        self.running = not self.running
        if self.running and (self._thread is None or not self._thread.is_alive()):
            self._thread = threading.Thread(target=self._tick, daemon=True)
            self._thread.start()
        self._refresh()

    def _tick(self):
        while self.running:
            time.sleep(1)
            if not self.running:
                break
            self.remaining -= 1
            if self.remaining <= 0:
                self.running = False
                self._finish()
                break
            self._refresh()

    def _finish(self):
        if self.mode == "Focus":
            self.shell.core.finish_focus_session(self.minutes)
            message = f"Focus session complete — {self.minutes} minutes added to today."
        else:
            message = "Break's over. Ready for another focus session?"
        self.remaining = self.minutes * 60
        self._refresh()
        self.shell.toast(message)
