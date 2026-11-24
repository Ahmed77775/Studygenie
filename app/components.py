"""Reusable building blocks, so every screen looks and behaves the same.

Interactive pieces are real buttons (focusable, keyboard-operable) with
visible default, hover, focus, pressed and disabled states."""

import flet as ft

from .prompts import LANGUAGE_WARNING, UNRELIABLE_LANGUAGES, language_label

from . import theme as t

States = ft.ControlState


# ------------------------------- surfaces ---------------------------------

def panel(content, elevated=False, padding=t.XL, radius=t.RADIUS, expand=None, col=None, **kwargs):
    """A solid content surface with a hairline border (glass is reserved for dialogs)."""
    return ft.Container(
        content=content,
        bgcolor=t.ELEVATED_GLASS if elevated else t.SURFACE_GLASS,
        border=ft.Border.all(1, t.BORDER),
        border_radius=radius,
        padding=padding,
        expand=expand,
        col=col if col is not None else 12,
        **kwargs,
    )


def section_header(title, action=None, subtitle=None):
    left = [t.text(title, t.SUBTITLE, weight=t.SEMIBOLD)]
    if subtitle:
        left.append(t.text(subtitle, t.CAPTION, t.MUTED))
    controls = [ft.Column(left, spacing=2, expand=True)]
    if action:
        controls.append(action)
    return ft.Row(controls, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def divider():
    return ft.Divider(height=1, thickness=1, color=t.BORDER)


# -------------------------------- buttons ----------------------------------

def _shape(radius=t.RADIUS):
    return ft.RoundedRectangleBorder(radius=radius)


def primary_button(label, on_click=None, icon=None, expand=None, disabled=False, tooltip=None):
    """The one filled accent button on a screen: the main action."""
    style = ft.ButtonStyle(
        bgcolor={States.DISABLED: t.TRACK, States.FOCUSED: t.ACCENT_HOVER, States.HOVERED: t.ACCENT_HOVER,
                 States.DEFAULT: t.ACCENT},
        color={States.DISABLED: t.DISABLED_TEXT, States.DEFAULT: t.BG},
        overlay_color={States.PRESSED: ft.Colors.with_opacity(0.12, t.BG), States.DEFAULT: ft.Colors.TRANSPARENT},
        # Teal is also the focus colour, so a focused teal button gets a light ring instead.
        side={States.FOCUSED: ft.BorderSide(2, t.TEXT), States.DEFAULT: ft.BorderSide(0, ft.Colors.TRANSPARENT)},
        shape=_shape(), padding=ft.Padding.symmetric(horizontal=t.L + 2, vertical=t.M),
        text_style=ft.TextStyle(size=t.BODY, weight=t.SEMIBOLD), elevation=0,
        animation_duration=t.QUICK,
    )
    return ft.FilledButton(content=label, icon=icon, on_click=on_click, style=style, expand=expand,
                           disabled=disabled, tooltip=tooltip)


def secondary_button(label, on_click=None, icon=None, expand=None, disabled=False, tooltip=None):
    style = ft.ButtonStyle(
        bgcolor={States.HOVERED: t.ELEVATED, States.DEFAULT: t.SURFACE},
        color={States.DISABLED: t.DISABLED_TEXT, States.DEFAULT: t.TEXT},
        icon_color={States.DISABLED: t.DISABLED_TEXT, States.DEFAULT: t.TEXT},
        overlay_color={States.PRESSED: t.PRESSED, States.DEFAULT: ft.Colors.TRANSPARENT},
        side={States.FOCUSED: ft.BorderSide(2, t.FOCUS_RING), States.DISABLED: ft.BorderSide(1, t.BORDER),
              States.DEFAULT: ft.BorderSide(1, t.BORDER_STRONG)},
        shape=_shape(), padding=ft.Padding.symmetric(horizontal=t.L, vertical=t.M),
        text_style=ft.TextStyle(size=t.BODY, weight=t.SEMIBOLD), animation_duration=t.QUICK,
    )
    return ft.OutlinedButton(content=label, icon=icon, on_click=on_click, style=style, expand=expand,
                             disabled=disabled, tooltip=tooltip)


def text_button(label, on_click=None, icon=None, color=t.ACCENT, tooltip=None, disabled=False):
    style = ft.ButtonStyle(
        color={States.DISABLED: t.DISABLED_TEXT, States.HOVERED: t.ACCENT_HOVER if color == t.ACCENT else color,
               States.DEFAULT: color},
        icon_color={States.DISABLED: t.DISABLED_TEXT, States.DEFAULT: color},
        overlay_color={States.HOVERED: t.HOVER, States.PRESSED: t.PRESSED, States.DEFAULT: ft.Colors.TRANSPARENT},
        side={States.FOCUSED: ft.BorderSide(2, t.FOCUS_RING), States.DEFAULT: ft.BorderSide(0, ft.Colors.TRANSPARENT)},
        shape=_shape(), padding=ft.Padding.symmetric(horizontal=t.M, vertical=t.S),
        text_style=ft.TextStyle(size=t.BODY, weight=t.SEMIBOLD),
    )
    return ft.TextButton(content=label, icon=icon, on_click=on_click, style=style, tooltip=tooltip, disabled=disabled)


def icon_button(icon, on_click=None, tooltip=None, color=t.MUTED, selected=False, size=t.ICON):
    return ft.IconButton(
        icon=icon, icon_size=size, on_click=on_click, tooltip=tooltip,
        style=ft.ButtonStyle(
            color={States.DEFAULT: t.ACCENT if selected else color, States.HOVERED: t.ACCENT if selected else t.TEXT},
            bgcolor={States.DEFAULT: t.ELEVATED if selected else ft.Colors.TRANSPARENT, States.HOVERED: t.HOVER},
            overlay_color={States.PRESSED: t.PRESSED, States.DEFAULT: ft.Colors.TRANSPARENT},
            side={States.FOCUSED: ft.BorderSide(2, t.FOCUS_RING), States.DEFAULT: ft.BorderSide(0, ft.Colors.TRANSPARENT)},
            shape=_shape(12),
        ),
    )


def row_button(content, on_click, selected=False, padding=None, tooltip=None, height=None):
    """A full-width, focusable list row (navigation, lists of items)."""
    return ft.TextButton(
        content=content, on_click=on_click, tooltip=tooltip, height=height,
        style=ft.ButtonStyle(
            bgcolor={States.DEFAULT: t.ELEVATED if selected else ft.Colors.TRANSPARENT,
                     States.HOVERED: t.ELEVATED if selected else t.HOVER},
            overlay_color={States.PRESSED: t.PRESSED, States.DEFAULT: ft.Colors.TRANSPARENT},
            side={States.FOCUSED: ft.BorderSide(2, t.FOCUS_RING), States.DEFAULT: ft.BorderSide(0, ft.Colors.TRANSPARENT)},
            shape=_shape(12), padding=padding if padding is not None else ft.Padding.symmetric(horizontal=t.M, vertical=t.S + 2),
            alignment=ft.Alignment.CENTER_LEFT,
        ),
    )


def chip(label, selected, on_click, icon=None):
    """A pill toggle. Selection is shown by fill AND a check icon, not colour alone."""
    return ft.TextButton(
        content=label, icon=ft.Icons.CHECK if selected else icon, on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor={States.DEFAULT: t.ELEVATED if selected else ft.Colors.TRANSPARENT, States.HOVERED: t.ELEVATED},
            color={States.DEFAULT: t.TEXT if selected else t.MUTED, States.HOVERED: t.TEXT},
            icon_color={States.DEFAULT: t.ACCENT},
            side={States.FOCUSED: ft.BorderSide(2, t.FOCUS_RING),
                  States.DEFAULT: ft.BorderSide(1, t.ACCENT if selected else t.BORDER_STRONG)},
            shape=_shape(t.RADIUS_PILL), padding=ft.Padding.symmetric(horizontal=t.M + 2, vertical=t.S),
            text_style=ft.TextStyle(size=t.CAPTION + 1, weight=t.SEMIBOLD),
        ),
    )


# ------------------------------ data display --------------------------------

def progress_bar(value, height=6, color=t.ACCENT, expand=None):
    return ft.ProgressBar(value=max(0.0, min(1.0, value or 0)), color=color, bgcolor=t.TRACK,
                          bar_height=height, border_radius=t.RADIUS_PILL, expand=expand)


def stat(value, label, icon, caption=None, col=None):
    """A compact figure: icon, large value, label; optional caption."""
    lines = [ft.Row([ft.Icon(icon, size=t.ICON, color=t.MUTED), t.text(label, t.CAPTION, t.MUTED)], spacing=t.S),
             t.text(value, t.TITLE + 4, weight=t.SEMIBOLD)]
    if caption:
        lines.append(t.text(caption, t.CAPTION, t.MUTED))
    return panel(ft.Column(lines, spacing=t.XS + 2), padding=t.L + 2, col=col)


def subject_icon(subject):
    return {
        "Mathematics": ft.Icons.FUNCTIONS, "Physics": ft.Icons.BOLT, "Chemistry": ft.Icons.SCIENCE_OUTLINED,
        "Biology": ft.Icons.ECO_OUTLINED, "Computer Science": ft.Icons.CODE, "English": ft.Icons.MENU_BOOK_OUTLINED,
        "History": ft.Icons.ACCOUNT_BALANCE_OUTLINED, "Economics": ft.Icons.TRENDING_UP,
    }.get(subject, ft.Icons.AUTO_STORIES_OUTLINED)


def bar_chart(values, labels, highlight=None, height=120, value_suffix=""):
    """Rounded vertical bars that share the available width; one bar can be highlighted."""
    top = max(max(values or [0]), 1)
    columns = []
    for i, (value, label) in enumerate(zip(values, labels)):
        bar_height = max(4, (height - 36) * value / top) if value else 4
        is_highlight = i == highlight
        columns.append(ft.Column(
            [t.text(f"{value}{value_suffix}" if value else "", t.CAPTION, t.TEXT if is_highlight else t.MUTED),
             ft.Container(height=bar_height, border_radius=8,
                          bgcolor=t.ACCENT if is_highlight else (t.BAR if value else t.TRACK),
                          animate=t.motion(t.CALM)),
             t.text(label, t.CAPTION, t.TEXT if is_highlight else t.MUTED, weight=t.SEMIBOLD if is_highlight else t.REGULAR)],
            spacing=t.XS, horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            alignment=ft.MainAxisAlignment.END, expand=True,
        ))
    return ft.Container(ft.Row(columns, spacing=t.S, vertical_alignment=ft.CrossAxisAlignment.END), height=height)


# ------------------------------- feedback -----------------------------------

def empty_state(icon, title, body, action=None):
    controls = [ft.Icon(icon, size=32, color=t.MUTED), t.text(title, t.SUBTITLE, weight=t.SEMIBOLD),
                t.text(body, t.BODY, t.MUTED, text_align=ft.TextAlign.CENTER)]
    if action:
        controls.append(ft.Container(action, padding=ft.Padding.only(top=t.S)))
    return ft.Container(ft.Column(controls, spacing=t.S, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=t.XXL, alignment=ft.Alignment.CENTER)


def loading(message):
    return ft.Row([ft.ProgressRing(width=16, height=16, stroke_width=2, color=t.ACCENT),
                   t.text(message, t.BODY, t.MUTED)], spacing=t.M)


def error_message(message, on_retry=None):
    """An inline error: icon + words (never colour alone), with an optional retry."""
    controls = [ft.Icon(ft.Icons.ERROR_OUTLINE, color=t.ERROR, size=t.ICON),
                t.text(message, t.BODY, t.ERROR, expand=True)]
    if on_retry:
        controls.append(text_button("Try again", on_retry, color=t.TEXT))
    return ft.Container(ft.Row(controls, spacing=t.M, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        bgcolor=ft.Colors.with_opacity(0.08, t.ERROR), border_radius=t.RADIUS,
                        border=ft.Border.all(1, ft.Colors.with_opacity(0.25, t.ERROR)), padding=t.M)


# -------------------------------- inputs -------------------------------------

def text_field(label=None, hint=None, multiline=False, min_lines=1, max_lines=1, value="", password=False,
               on_submit=None, expand=None, autofocus=False, keyboard=None, max_length=None):
    return ft.TextField(
        label=label, hint_text=hint, value=value, multiline=multiline, min_lines=min_lines,
        max_lines=max_lines if not multiline else max(max_lines, min_lines), password=password,
        can_reveal_password=password, on_submit=on_submit, expand=expand, autofocus=autofocus,
        keyboard_type=keyboard, max_length=max_length, shift_enter=multiline,
        text_size=t.BODY, color=t.TEXT, cursor_color=t.ACCENT,
        filled=True, fill_color=t.BG,
        border_color=t.BORDER_STRONG, focused_border_color=t.ACCENT, border_radius=t.RADIUS,
        label_style=ft.TextStyle(color=t.MUTED), hint_style=ft.TextStyle(color=t.MUTED),
        content_padding=ft.Padding.symmetric(horizontal=t.L, vertical=t.M + 2),
    )


def dropdown(label, options, value, on_change=None, width=None, expand=None, option_text=None):
    return ft.Dropdown(
        label=label, value=value,
        options=[ft.DropdownOption(key=o, text=option_text(o) if option_text else o) for o in options],
        on_select=on_change, width=width, expand=expand, text_size=t.BODY, color=t.TEXT,
        filled=True, fill_color=t.BG, border_color=t.BORDER_STRONG, focused_border_color=t.ACCENT,
        border_radius=t.RADIUS, bgcolor=t.NAV, menu_height=360,
        content_padding=ft.Padding.symmetric(horizontal=t.L, vertical=t.M),
    )


def language_dropdown(core, label="Language", on_change=None, expand=None, width=None):
    """The AI teaching language. Changing it anywhere saves it for every screen."""
    def changed(e):
        core.save_teaching_language(e.control.value)
        if on_change:
            on_change(e.control.value)
    return dropdown(label, core.LANGUAGES, core.teaching_language, changed, width=width, expand=expand,
                    option_text=language_label)


def language_note(core):
    """A short warning shown only when an unreliable language is selected."""
    if core.teaching_language not in UNRELIABLE_LANGUAGES:
        return None
    return ft.Row([ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=t.MUTED),
                   t.text(LANGUAGE_WARNING, t.CAPTION, t.MUTED, expand=True)], spacing=t.S,
                  vertical_alignment=ft.CrossAxisAlignment.START)


def markdown(value):
    """AI answers: headings, bold, lists and code, styled for reading."""
    return ft.Markdown(value, selectable=True, extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                       code_theme="atom-one-dark")
