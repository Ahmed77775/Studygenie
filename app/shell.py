"""The app frame: navigation, header and the content area, adapting to
screen size.

  desktop  (>= 1100 px): full sidebar (collapsible to a rail), header, content
  tablet   (640-1099):   icon rail (expandable), header, content
  phone    (< 640):      compact header, content, fixed bottom navigation

Pages are classes in app/views with a `title` and a `build()` that
returns a control. The shell owns navigation; pages ask it to navigate,
show a message, or refresh the header."""

from pathlib import Path

import flet as ft

from . import components as c
from . import theme as t
from .focus_timer import FocusTimer
from .views import dashboard, flashcards, learn, notes, pdf_maker, practice, progress, sketchpad, teacher

# key, label, icon, selected icon, page class, group
PAGES = (
    ("dashboard", "Dashboard", ft.Icons.SPACE_DASHBOARD_OUTLINED, ft.Icons.SPACE_DASHBOARD, dashboard.DashboardPage, "main"),
    ("learn", "Learn", ft.Icons.PHOTO_CAMERA_OUTLINED, ft.Icons.PHOTO_CAMERA, learn.LearnPage, "main"),
    ("practice", "Practice", ft.Icons.QUIZ_OUTLINED, ft.Icons.QUIZ, practice.PracticePage, "main"),
    ("teacher", "AI Teacher", ft.Icons.CHAT_BUBBLE_OUTLINE, ft.Icons.CHAT_BUBBLE, teacher.TeacherPage, "main"),
    ("flashcards", "Flashcards", ft.Icons.STYLE_OUTLINED, ft.Icons.STYLE, flashcards.FlashcardsPage, "main"),
    ("progress", "Progress", ft.Icons.INSIGHTS_OUTLINED, ft.Icons.INSIGHTS, progress.ProgressPage, "main"),
    ("notes", "Notes", ft.Icons.STICKY_NOTE_2_OUTLINED, ft.Icons.STICKY_NOTE_2, notes.NotesPage, "tools"),
    ("sketchpad", "Sketchpad", ft.Icons.BRUSH_OUTLINED, ft.Icons.BRUSH, sketchpad.SketchpadPage, "tools"),
    ("pdf_maker", "PDF Maker", ft.Icons.PICTURE_AS_PDF_OUTLINED, ft.Icons.PICTURE_AS_PDF, pdf_maker.PdfMakerPage,
     "tools"),
)
PAGE_BY_KEY = {p[0]: p for p in PAGES}

# Phones show five tabs at most. AI Teacher gets a tab because it's used
# constantly; Progress lives in "More" and in the avatar menu.
PHONE_TABS = ("dashboard", "learn", "teacher", "practice")   # + "More"
PHONE_TAB_LABELS = {"dashboard": "Home"}


class Shell:
    def __init__(self, page: ft.Page, core, on_sign_out):
        self.page = page
        self.core = core
        self.on_sign_out = on_sign_out
        self.route = "dashboard"
        self.params = {}
        self.layout = t.layout_for(page.width or 1280)
        self.rail_expanded = False      # tablet: user opened the full sidebar
        self.sidebar_collapsed = False  # desktop: user collapsed to the rail
        self.tools_open = True
        self.pages = {}
        self._saver = None  # FilePicker used to save files, made on first use
        self.timer = FocusTimer(self)
        self.content_host = ft.Container(expand=True)
        self.header_stats = ft.Row(spacing=t.S, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        self.header_title = t.text("", t.TITLE, weight=t.SEMIBOLD, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS)
        core.subscribe(self._on_core_event)
        page.on_resize = self._on_resize

    # ------------------------------ lifecycle ------------------------------

    def start(self):
        self.navigate("dashboard")

    def _on_resize(self, _e=None):
        layout = t.layout_for(self.page.width or 1280)
        if layout != self.layout:
            self.layout = layout
            self.rail_expanded = False
            self.render()

    def _on_core_event(self, kind, info):
        if kind == "status":
            self.refresh_header()
        elif kind == "celebrate":
            self.toast(info.get("title", ""))

    # ------------------------------ navigation -----------------------------

    def navigate(self, key, **params):
        if key not in PAGE_BY_KEY:
            key = "dashboard"
        current = self.pages.get(self.route)
        if current is not None and hasattr(current, "on_leave"):
            current.on_leave()
        self.route, self.params = key, params
        if self.layout == "tablet":
            self.rail_expanded = False
        self.render()

    def refresh(self, view):
        """Redraws `view` if it is the page on screen (results arriving from
        a worker thread for a page the learner has left are just kept)."""
        if self.pages.get(self.route) is view:
            self.render()

    def page_object(self, key):
        if key not in self.pages:
            self.pages[key] = PAGE_BY_KEY[key][4](self)
        return self.pages[key]

    # ------------------------------- render --------------------------------

    def render(self):
        view = self.page_object(self.route)
        self.header_title.value = view.title
        body = view.build(**self.params) if self.params else view.build()
        self.content_host.content = self._frame_content(body, getattr(view, "scrolls_itself", False))
        self.content_host.padding = (ft.Padding.symmetric(horizontal=t.L, vertical=t.M) if self.layout == "phone"
                                     else ft.Padding.only(left=t.XL, right=t.XL, top=t.S, bottom=t.XL))
        self.refresh_header(update=False)
        self.page.controls.clear()
        self.page.add(self._phone_layout() if self.layout == "phone" else self._wide_layout())
        self.page.update()

    def _frame_content(self, body, scrolls_itself):
        """Centres the page in a readable column; scrolls only if the page doesn't."""
        if scrolls_itself:
            inner = ft.Container(body, expand=True, width=t.CONTENT_MAX)
            return ft.Row([inner], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                          expand=True)
        column = ft.Column([ft.Container(body, width=t.CONTENT_MAX)], scroll=ft.ScrollMode.AUTO, expand=True,
                           horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        return column

    def _wide_layout(self):
        full = (self.layout == "desktop" and not self.sidebar_collapsed) or (self.layout == "tablet" and self.rail_expanded)
        nav = self._sidebar() if full else self._rail()
        main = ft.Column([self._header(), self.content_host], spacing=0, expand=True)
        return ft.Row([nav, main], spacing=0, expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH)

    def _phone_layout(self):
        return ft.Column([self._header(), self.content_host, self._bottom_nav()], spacing=0, expand=True)

    # ------------------------------- sidebar -------------------------------

    def _logo(self, compact=False):
        mark = ft.Container(t.text("S", t.SUBTITLE, t.ACCENT, t.SEMIBOLD), width=34, height=34, bgcolor=t.ELEVATED,
                            border_radius=10, alignment=ft.Alignment.CENTER)
        if compact:
            return mark
        return ft.Row([mark, ft.Column([t.text("StudyGenie", t.SUBTITLE, weight=t.SEMIBOLD),
                                        t.text("AI Study Companion", t.CAPTION, t.MUTED)], spacing=0)],
                      spacing=t.M)

    def _nav_row(self, key):
        _, label, icon, icon_on, _, _ = PAGE_BY_KEY[key]
        selected = key == self.route
        indicator = ft.Container(width=3, height=18, border_radius=2,
                                 bgcolor=t.ACCENT if selected else ft.Colors.TRANSPARENT)
        content = ft.Row([indicator,
                          ft.Icon(icon_on if selected else icon, size=t.NAV_ICON, color=t.ACCENT if selected else t.MUTED),
                          t.text(label, t.BODY, t.TEXT if selected else t.MUTED,
                                 t.SEMIBOLD if selected else t.REGULAR)], spacing=t.M - 2)
        return c.row_button(content, lambda _e, k=key: self.navigate(k), selected=selected, height=44,
                            padding=ft.Padding.only(left=t.XS, right=t.M))

    def _sidebar(self):
        main_rows = [self._nav_row(p[0]) for p in PAGES if p[5] == "main"]
        tools_header = c.row_button(
            ft.Row([t.text("Tools", t.CAPTION, t.MUTED, t.SEMIBOLD, expand=True),
                    ft.Icon(ft.Icons.EXPAND_LESS if self.tools_open else ft.Icons.EXPAND_MORE, size=18, color=t.MUTED)]),
            self._toggle_tools, height=36, tooltip="Show or hide tools")
        tool_rows = [self._nav_row(p[0]) for p in PAGES if p[5] == "tools"] if self.tools_open else []
        collapse = c.icon_button(ft.Icons.KEYBOARD_DOUBLE_ARROW_LEFT, self._toggle_sidebar, "Collapse sidebar")
        return ft.Container(
            ft.Column([
                ft.Row([self._logo(), collapse], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(height=t.L),
                *main_rows,
                ft.Container(height=t.M),
                tools_header,
                *tool_rows,
            ], spacing=2, scroll=ft.ScrollMode.AUTO, expand=True),
            width=244, bgcolor=t.NAV, padding=ft.Padding.symmetric(horizontal=t.M, vertical=t.L),
            border=ft.Border.only(right=ft.BorderSide(1, t.BORDER)),
        )

    def _rail(self):
        def rail_button(key):
            _, label, icon, icon_on, _, _ = PAGE_BY_KEY[key]
            selected = key == self.route
            return c.icon_button(icon_on if selected else icon, lambda _e, k=key: self.navigate(k), label,
                                 color=t.MUTED, selected=selected, size=t.NAV_ICON)

        expand = c.icon_button(ft.Icons.KEYBOARD_DOUBLE_ARROW_RIGHT, self._toggle_sidebar, "Expand sidebar")
        mains = [rail_button(p[0]) for p in PAGES if p[5] == "main"]
        tools = [rail_button(p[0]) for p in PAGES if p[5] == "tools"]
        return ft.Container(
            ft.Column([self._logo(compact=True), ft.Container(height=t.M), *mains,
                       ft.Container(ft.Divider(height=1, color=t.BORDER), width=32, padding=ft.Padding.symmetric(vertical=t.S)),
                       *tools, ft.Container(expand=True), expand],
                      spacing=t.S, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO),
            width=72, bgcolor=t.NAV, padding=ft.Padding.symmetric(vertical=t.L),
            border=ft.Border.only(right=ft.BorderSide(1, t.BORDER)),
        )

    def _toggle_sidebar(self, _e=None):
        if self.layout == "desktop":
            self.sidebar_collapsed = not self.sidebar_collapsed
        else:
            self.rail_expanded = not self.rail_expanded
        self.render()

    def _toggle_tools(self, _e=None):
        self.tools_open = not self.tools_open
        self.render()

    # ------------------------------- header --------------------------------

    def _header(self):
        phone = self.layout == "phone"
        self.header_title.expand = True  # long titles shorten with "…" instead of running under the icons
        left = [self.header_title]  # phones skip the logo: the title needs the room
        return ft.Container(
            ft.Row([ft.Row(left, spacing=0, expand=True), self.header_stats],
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=56 if phone else 64,
            padding=ft.Padding.symmetric(horizontal=t.L if phone else t.XL),
            bgcolor=t.NAV if phone else None,
            border=ft.Border.only(bottom=ft.BorderSide(1, t.BORDER)) if phone else None,
        )

    def refresh_header(self, update=True):
        core = self.core
        info = core.level_info()
        streak = core.data.get("streak_days", 0)
        phone = self.layout == "phone"

        def pill(icon, label, tooltip):
            return ft.Container(
                ft.Row([ft.Icon(icon, size=16, color=t.MUTED), t.text(label, t.CAPTION + 1, weight=t.SEMIBOLD)],
                       spacing=t.XS + 2),
                padding=ft.Padding.symmetric(horizontal=t.M, vertical=t.XS + 2), border_radius=t.RADIUS_PILL,
                border=ft.Border.all(1, t.BORDER), tooltip=tooltip,
            )

        controls = [self.timer.header_button(compact=phone)]
        if not phone:  # on phones XP is on the dashboard and in the profile menu, leaving room for the title
            controls.append(pill(ft.Icons.BOLT, f"{info['total']:,} XP",
                                 f"Total XP · Level {info['level']} {info['title']}"))
        controls.append(pill(ft.Icons.LOCAL_FIRE_DEPARTMENT_OUTLINED, f"{streak}" if phone else
                             f"{streak} day{'s' if streak != 1 else ''}", "Learning streak"))
        controls.append(self._profile_menu())
        self.header_stats.controls = controls
        if update:
            try:
                self.header_stats.update()
            except Exception:
                pass  # not on the page yet

    def _profile_menu(self):
        core = self.core
        info = core.level_info()
        profile = core.profile or {}
        avatar = ft.Container(t.text(profile.get("avatar") or core.display_name[:1], t.SUBTITLE),
                              width=36, height=36, border_radius=18, bgcolor=t.ELEVATED, alignment=ft.Alignment.CENTER)
        summary = ft.Column([
            t.text(core.display_name, t.SUBTITLE, weight=t.SEMIBOLD),
            t.text(f"Level {info['level']} — {info['title']}", t.BODY, t.MUTED),
            c.progress_bar(info["xp"] / info["needed"]),
            t.text(f"{info['xp']} / {info['needed']} XP", t.CAPTION, t.MUTED),
        ], spacing=t.S, width=220)
        return ft.PopupMenuButton(
            content=avatar, tooltip="Your profile", bgcolor=t.NAV, menu_padding=t.S,
            items=[ft.PopupMenuItem(content=summary, disabled=True),
                   ft.PopupMenuItem(content=ft.Row([ft.Icon(ft.Icons.INSIGHTS, size=t.ICON, color=t.MUTED),
                                                    t.text("View progress")]),
                                    on_click=lambda _e: self.navigate("progress")),
                   ft.PopupMenuItem(content=ft.Row([ft.Icon(ft.Icons.LOGOUT, size=t.ICON, color=t.MUTED),
                                                    t.text("Switch profile")]),
                                    on_click=lambda _e: self.on_sign_out())],
        )

    # ----------------------------- phone nav --------------------------------

    def _bottom_nav(self):
        keys = list(PHONE_TABS)
        selected = keys.index(self.route) if self.route in keys else len(keys)
        destinations = [ft.NavigationBarDestination(
            label=PHONE_TAB_LABELS.get(k, PAGE_BY_KEY[k][1]), icon=PAGE_BY_KEY[k][2], selected_icon=PAGE_BY_KEY[k][3])
            for k in keys]
        destinations.append(ft.NavigationBarDestination(label="More", icon=ft.Icons.MENU, selected_icon=ft.Icons.MENU_OPEN))

        def changed(e):
            index = int(e.control.selected_index)
            if index < len(keys):
                self.navigate(keys[index])
            else:
                self._open_more()

        return ft.NavigationBar(destinations=destinations, selected_index=selected, on_change=changed,
                                bgcolor=t.NAV, indicator_color=ft.Colors.with_opacity(0.16, t.ACCENT), height=68,
                                label_behavior=ft.NavigationBarLabelBehavior.ALWAYS_SHOW,
                                border=ft.Border.only(top=ft.BorderSide(1, t.BORDER)))

    def _open_more(self):
        rows = []
        for key, label, icon, icon_on, _, _ in PAGES:
            if key in PHONE_TABS:
                continue
            selected = key == self.route
            rows.append(c.row_button(
                ft.Row([ft.Icon(icon_on if selected else icon, color=t.ACCENT if selected else t.MUTED),
                        t.text(label, t.SUBTITLE)], spacing=t.L),
                lambda _e, k=key: (self.page.pop_dialog(), self.navigate(k)), selected=selected, height=t.TOUCH + 4))
        sheet = ft.BottomSheet(
            ft.Container(ft.Column([t.text("More", t.CAPTION, t.MUTED, t.SEMIBOLD), *rows], spacing=t.XS, tight=True),
                         padding=ft.Padding.only(left=t.L, right=t.L, top=t.L, bottom=t.XL)),
            bgcolor=t.DIALOG, show_drag_handle=True, on_dismiss=lambda _e: self.render())
        self.page.show_dialog(sheet)

    # ------------------------------- helpers --------------------------------

    def toast(self, message):
        """A brief, quiet confirmation at the bottom of the screen."""
        if not message:
            return
        self.page.show_dialog(ft.SnackBar(t.text(message, t.BODY, t.TEXT), bgcolor=t.ELEVATED,
                                          behavior=ft.SnackBarBehavior.FLOATING, duration=3000,
                                          width=None if self.layout == "phone" else 420))

    def confirm(self, title, message, confirm_label, on_confirm):
        def close(_e=None):
            self.page.pop_dialog()

        def accept(_e=None):
            self.page.pop_dialog()
            on_confirm()

        self.page.show_dialog(ft.AlertDialog(
            title=t.text(title, t.TITLE, weight=t.SEMIBOLD), content=t.text(message, t.BODY, t.MUTED),
            actions=[c.text_button("Cancel", close, color=t.TEXT), c.primary_button(confirm_label, accept)],
            bgcolor=t.DIALOG, shape=ft.RoundedRectangleBorder(radius=t.RADIUS_LARGE)))

    async def save_file(self, data, file_name, what):
        """Saves `data` (bytes): a save dialog in the desktop window, a
        download in a browser. `what` names it in messages, e.g. "Your PDF"."""
        if self._saver is None:
            self._saver = ft.FilePicker()
            self.page.services.append(self._saver)
            self.page.update()
        try:
            path = await self._saver.save_file(dialog_title=f"Save {what.lower()}", file_name=file_name,
                                               src_bytes=data)
            if self.page.web:
                self.toast(f"{what} is downloading")
                return True
            if not path:
                return False  # the dialog was cancelled
            target = Path(path)
            if not target.exists() or target.stat().st_size == 0:
                target.write_bytes(data)  # some platforms only create the file
        except Exception:
            self.toast(f"{what} couldn't be saved. Please try again.")
            return False
        self.toast(f"{what} was saved to {target.name}")
        return True

    def columns(self, desktop, tablet=None, phone=12):
        """Responsive column spans for a ResponsiveRow (12-column grid)."""
        return {"xs": phone, "md": tablet if tablet is not None else desktop, "xl": desktop}
