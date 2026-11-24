"""PDF Maker: a document title plus pages (each a heading and body text),
reorderable, exported as a real PDF. A saved note can be added as a page.

Edits are kept as you type, so switching pages never loses text. The
document lasts for the session; the exported PDF is what you keep."""

import re

import flet as ft

from .. import components as c
from .. import pdf
from .. import theme as t


class PdfMakerPage:
    title = "PDF Maker"

    def __init__(self, shell):
        self.shell = shell
        self.core = shell.core
        self.doc_title = "Untitled document"
        self.pages = []            # {"heading": str, "body": str}
        self.index = None          # page being edited
        self.editing = False       # phones: showing the editor instead of the list
        self.exporting = False

    # ------------------------------- layout --------------------------------

    def build(self):
        intro = ft.Column([t.text("PDF Maker", t.DISPLAY, weight=t.SEMIBOLD),
                           t.text("Turn a title and a few pages of text into a real PDF.", t.SUBTITLE, t.MUTED)],
                          spacing=t.XS)
        if not pdf.available():
            return ft.Column([intro, c.panel(c.empty_state(
                ft.Icons.PICTURE_AS_PDF_OUTLINED, "PDF Maker needs fpdf2",
                "Install the packages in requirements.txt, then reopen this page."))], spacing=t.XL)
        if self.pages:
            self.index = max(0, min(self.index or 0, len(self.pages) - 1))
        else:
            self.index = None
        phone = self.shell.layout == "phone"
        if phone:
            body = self._editor() if (self.editing and self.index is not None) else self._page_list()
        else:
            body = ft.ResponsiveRow([ft.Container(self._page_list(), col={"xs": 12, "md": 4}),
                                     ft.Container(self._editor(), col={"xs": 12, "md": 8})],
                                    spacing=t.XL, run_spacing=t.XL)
        return ft.Column([intro, self._title_bar(), body], spacing=t.XL)

    def _title_bar(self):
        field = c.text_field("Document title", value=self.doc_title, expand=True)
        field.on_change = lambda e: setattr(self, "doc_title", e.control.value)
        has_content = any(p["heading"].strip() or p["body"].strip() for p in self.pages)
        export = (c.loading("Making your PDF…") if self.exporting else
                  c.primary_button("Export PDF", self._export, icon=ft.Icons.DOWNLOAD, disabled=not has_content,
                                   tooltip=None if has_content else "Add a page with some text first"))
        return c.panel(ft.Row([field, export], spacing=t.M, wrap=self.shell.layout == "phone",
                              vertical_alignment=ft.CrossAxisAlignment.CENTER), padding=t.L)

    def _page_list(self):
        header = ft.Row([t.text("Pages", t.SUBTITLE, weight=t.SEMIBOLD, expand=True),
                         c.icon_button(ft.Icons.NOTE_ADD_OUTLINED, self._from_note, "Add a saved note as a page"),
                         c.secondary_button("Add page", self._add, icon=ft.Icons.ADD)],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER)
        if not self.pages:
            return c.panel(ft.Column([header, c.empty_state(
                ft.Icons.DESCRIPTION_OUTLINED, "No pages yet",
                "Add a page and write a heading and some text, or start from one of your notes.")], spacing=t.L))
        rows = [c.row_button(
            ft.Row([t.text(f"{i + 1}", t.CAPTION, t.MUTED, t.SEMIBOLD, width=20),
                    t.text(page["heading"].strip() or "Untitled page", t.BODY, expand=True, no_wrap=True,
                           overflow=ft.TextOverflow.ELLIPSIS)], spacing=t.S),
            lambda _e, i=i: self._open(i), selected=i == self.index)
            for i, page in enumerate(self.pages)]
        move = ft.Row([
            c.text_button("Move up", lambda _e: self._move(-1), icon=ft.Icons.ARROW_UPWARD, color=t.TEXT,
                          disabled=not self.index),
            c.text_button("Move down", lambda _e: self._move(1), icon=ft.Icons.ARROW_DOWNWARD, color=t.TEXT,
                          disabled=self.index is None or self.index >= len(self.pages) - 1),
        ], wrap=True, spacing=0)
        count = t.text(f"{len(self.pages)} page{'s' if len(self.pages) != 1 else ''}", t.CAPTION, t.MUTED)
        return c.panel(ft.Column([header, ft.Column(rows, spacing=t.XS), move, count], spacing=t.M), padding=t.L)

    def _editor(self):
        if self.index is None:
            return c.panel(c.empty_state(ft.Icons.EDIT_NOTE, "Add your first page",
                                         "Each page gets a heading and body text. The PDF starts with a title page.",
                                         c.primary_button("Add a page", self._add, icon=ft.Icons.ADD)))
        page = self.pages[self.index]
        heading = c.text_field("Page heading", value=page["heading"])
        body = c.text_field("Page text", multiline=True, min_lines=14, max_lines=30, value=page["body"])
        heading.on_change = lambda e: self._edit("heading", e.control.value)
        heading.on_blur = lambda _e: self.shell.refresh(self)  # the list shows the new heading
        body.on_change = lambda e: self._edit("body", e.control.value)
        top = []
        if self.shell.layout == "phone":
            top.append(c.text_button("All pages", lambda _e: self._back(), icon=ft.Icons.ARROW_BACK, color=t.TEXT))
        actions = ft.Row([c.text_button("Delete page", self._delete, icon=ft.Icons.DELETE_OUTLINE, color=t.MUTED),
                          ft.Container(expand=True),
                          t.text(f"Page {self.index + 1} of {len(self.pages)}", t.CAPTION, t.MUTED)])
        return c.panel(ft.Column([*top, heading, body, actions], spacing=t.M,
                                 horizontal_alignment=ft.CrossAxisAlignment.STRETCH))

    # ------------------------------- actions -------------------------------

    def _edit(self, field, value):
        if self.index is not None:
            self.pages[self.index][field] = value

    def _open(self, index):
        self.index, self.editing = index, True
        self.shell.refresh(self)

    def _back(self):
        self.editing = False
        self.shell.refresh(self)

    def _add(self, _e=None, heading=None, body=""):
        self.pages.append({"heading": heading or f"Page {len(self.pages) + 1}", "body": body})
        self._open(len(self.pages) - 1)

    def _move(self, step):
        i = self.index
        j = (i or 0) + step
        if i is None or not 0 <= j < len(self.pages):
            return
        self.pages[i], self.pages[j] = self.pages[j], self.pages[i]
        self.index = j
        self.shell.refresh(self)

    def _delete(self, _e=None):
        def remove():
            del self.pages[self.index]
            self.index = max(0, self.index - 1) if self.pages else None
            self.editing = self.index is not None and self.editing
            self.shell.refresh(self)
        self.shell.confirm("Delete this page?", "Its heading and text will be removed from the document.",
                           "Delete", remove)

    def _from_note(self, _e=None):
        notes = self.core.notes_newest_first()
        if not notes:
            self.shell.toast("You don't have any saved notes yet.")
            return

        def choose(note):
            self.shell.page.pop_dialog()
            self._add(heading=note["title"], body=note["content"])

        rows = [c.row_button(ft.Column([
            t.text(n["title"] or "Untitled note", t.BODY, weight=t.SEMIBOLD, no_wrap=True,
                   overflow=ft.TextOverflow.ELLIPSIS),
            t.text(" ".join(n["content"].split())[:80], t.CAPTION, t.MUTED, max_lines=1,
                   overflow=ft.TextOverflow.ELLIPSIS)], spacing=2), lambda _e, n=n: choose(n))
            for n in notes]
        self.shell.page.show_dialog(ft.AlertDialog(
            title=t.text("Add a note as a page", t.TITLE, weight=t.SEMIBOLD),
            content=ft.Container(ft.Column(rows, spacing=t.XS, scroll=ft.ScrollMode.AUTO), width=420, height=360),
            actions=[c.text_button("Cancel", lambda _e: self.shell.page.pop_dialog(), color=t.TEXT)],
            bgcolor=t.DIALOG, shape=ft.RoundedRectangleBorder(radius=t.RADIUS_LARGE)))

    async def _export(self, _e=None):
        pages = [{"heading": p["heading"].strip(), "body": p["body"].strip()} for p in self.pages]
        pages = [p for p in pages if p["heading"] or p["body"]]
        if not pages or self.exporting:
            return
        title = self.doc_title.strip() or "Untitled document"
        self.exporting = True
        self.shell.refresh(self)
        try:
            data = pdf.document(title, pages)
        except Exception:
            self.exporting = False
            self.shell.refresh(self)
            self.shell.toast("The PDF couldn't be made. Please try again.")
            return
        self.exporting = False
        self.shell.refresh(self)
        file_name = (re.sub(r"[^A-Za-z0-9_-]+", "_", title).strip("_") or "studygenie_document") + ".pdf"
        if await self.shell.save_file(data, file_name, "Your PDF"):
            self.core.made_pdf(6)
