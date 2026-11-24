"""Profile sign-in: create a local profile, or come back to one (with its
optional PIN)."""

import flet as ft

from . import components as c
from . import theme as t


class SignIn:
    def __init__(self, page: ft.Page, core, on_ready):
        self.page = page
        self.core = core
        self.on_ready = on_ready
        self.creating = not core.has_profile
        self.avatar = core.AVATARS[0]

    def show(self):
        self.page.controls.clear()
        card = c.panel(self._create_form() if self.creating else self._welcome_form(), padding=t.XXL,
                       radius=t.RADIUS_LARGE)
        card.width = 420
        brand = ft.Column([
            ft.Container(t.text("S", t.TITLE, t.ACCENT, t.SEMIBOLD), width=48, height=48, bgcolor=t.ELEVATED,
                         border_radius=14, alignment=ft.Alignment.CENTER),
            t.text("StudyGenie – AI Study Companion", t.TITLE, weight=t.SEMIBOLD, text_align=ft.TextAlign.CENTER),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=t.M)
        self.page.add(ft.Container(
            ft.Column([brand, card], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=t.XL,
                      scroll=ft.ScrollMode.AUTO),
            alignment=ft.Alignment.CENTER, expand=True, padding=t.L))
        self.page.update()

    # ------------------------------- forms ---------------------------------

    def _create_form(self):
        name = c.text_field("Your name", autofocus=True, max_length=40)
        pin = c.text_field("PIN (optional, 4–6 digits)", password=True, keyboard=ft.KeyboardType.NUMBER,
                           max_length=6)
        message = ft.Container()

        def avatar_button(emoji):
            selected = emoji == self.avatar
            return ft.Container(
                ft.TextButton(content=t.text(emoji, t.TITLE), on_click=lambda _e, a=emoji: pick(a),
                              tooltip="Selected avatar" if selected else "Choose this avatar",
                              style=ft.ButtonStyle(
                                  shape=ft.RoundedRectangleBorder(radius=12), padding=t.S,
                                  bgcolor={ft.ControlState.DEFAULT: t.ELEVATED if selected else ft.Colors.TRANSPARENT,
                                           ft.ControlState.HOVERED: t.ELEVATED},
                                  side={ft.ControlState.FOCUSED: ft.BorderSide(2, t.FOCUS_RING),
                                        ft.ControlState.DEFAULT: ft.BorderSide(2 if selected else 1,
                                                                                 t.ACCENT if selected else t.BORDER)})),
            )

        avatars = ft.Row([avatar_button(a) for a in self.core.AVATARS], wrap=True, spacing=t.S, run_spacing=t.S)

        def pick(emoji):
            self.avatar = emoji
            avatars.controls = [avatar_button(a) for a in self.core.AVATARS]
            avatars.update()

        def create(_e=None):
            try:
                self.core.create_profile(name.value, self.avatar, pin.value)
            except (ValueError, OSError) as exc:
                message.content = c.error_message(str(exc))
                message.update()
                return
            self._enter()

        def skip(_e=None):
            self.core.create_profile("Guest", "✦")
            self._enter()

        name.on_submit = create
        pin.on_submit = create
        return ft.Column([
            t.text("Create your profile", t.TITLE, weight=t.SEMIBOLD),
            t.text("Everything stays on this computer.", t.BODY, t.MUTED),
            ft.Container(height=t.S), name,
            t.text("Avatar", t.CAPTION, t.MUTED, t.SEMIBOLD), avatars,
            pin, message,
            c.primary_button("Start studying", create, expand=True),
            ft.Row([c.text_button("Skip for now", skip, color=t.MUTED)], alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=t.M, tight=True)

    def _welcome_form(self):
        profile = self.core.data["profile"]
        info = self.core.level_info()
        streak = self.core.data.get("streak_days", 0)
        message = ft.Container()
        pin = None
        if profile.get("pin_hash"):
            pin = c.text_field("PIN", password=True, keyboard=ft.KeyboardType.NUMBER, max_length=6, autofocus=True)

        def go(_e=None):
            if pin is not None and not self.core.pin_matches(pin.value):
                pin.value = ""
                message.content = c.error_message("That PIN doesn't match. Try again.")
                self.page.update()
                return
            self._enter()

        def switch(_e=None):
            self.creating = True
            self.show()

        if pin is not None:
            pin.on_submit = go
        rows = [
            ft.Row([ft.Container(t.text(profile.get("avatar") or "✦", t.TITLE), width=52, height=52,
                                 bgcolor=t.ELEVATED, border_radius=26, alignment=ft.Alignment.CENTER),
                    ft.Column([t.text(f"Welcome back, {profile.get('name') or 'Student'}", t.SUBTITLE, weight=t.SEMIBOLD),
                               t.text(f"Level {info['level']} — {info['title']}  ·  {streak} day streak", t.BODY, t.MUTED)],
                              spacing=2, expand=True)], spacing=t.L),
        ]
        if pin is not None:
            rows.append(pin)
        rows += [message, c.primary_button("Continue", go, expand=True),
                 ft.Row([c.text_button("Use a different profile", switch, color=t.MUTED)],
                        alignment=ft.MainAxisAlignment.CENTER)]
        return ft.Column(rows, spacing=t.M, tight=True)

    def _enter(self):
        self.core.sign_in()
        self.on_ready()
