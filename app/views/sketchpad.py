"""Sketchpad: draw a diagram, mind-map or labelled figure, then save it
as a PNG. Works with a mouse, a pen or a finger.

Strokes are kept in "board" coordinates (a fixed 880 x 460 board), so the
drawing scales with the screen and the saved image matches what was drawn."""

import io

import flet as ft
import flet.canvas as cv

from .. import components as c
from .. import theme as t
from ..deps import Image, ImageDraw

BOARD_W, BOARD_H = 880, 460
EXPORT_SCALE = 2  # the PNG is twice the board size, so lines stay crisp
PAPER = "#FFFFFF"
INKS = (("Ink", "#1B2440"), ("Teal", "#0D9488"), ("Blue", "#2563EB"), ("Pink", "#DB2777"),
        ("Amber", "#CA8A04"), ("Red", "#DC2626"), ("Green", "#16A34A"))


class SketchpadPage:
    title = "Sketchpad"

    def __init__(self, shell):
        self.shell = shell
        self.core = shell.core
        self.strokes = []          # {"color", "width", "points": [(x, y), ...]} in board coordinates
        self.color = INKS[0][1]
        self.width = 4
        self.scale = 1.0           # screen pixels per board unit, from the canvas size
        self._canvas = None

    # ------------------------------- layout --------------------------------

    def build(self):
        intro = ft.Column([t.text("Sketchpad", t.DISPLAY, weight=t.SEMIBOLD),
                           t.text("Sketch a quick diagram, mind-map or figure, then save it as an image.",
                                  t.SUBTITLE, t.MUTED)], spacing=t.XS)
        if Image is None:
            return ft.Column([intro, c.panel(c.empty_state(
                ft.Icons.BRUSH_OUTLINED, "Sketchpad needs Pillow",
                "Install the packages in requirements.txt, then reopen this page."))], spacing=t.XL)
        self._canvas = cv.Canvas(
            shapes=self._shapes(), aspect_ratio=BOARD_W / BOARD_H, on_resize=self._resized,
            content=ft.GestureDetector(on_pan_start=self._start, on_pan_update=self._move, on_tap_up=self._dot,
                                       drag_interval=10, mouse_cursor=ft.MouseCursor.PRECISE))
        board = ft.Container(self._canvas, bgcolor=PAPER, border_radius=t.RADIUS, clip_behavior=ft.ClipBehavior.HARD_EDGE,
                             border=ft.Border.all(1, t.BORDER))
        hint = t.text("Drag to draw · tap for a dot · Undo removes the last line", t.CAPTION, t.MUTED)
        return ft.Column([intro, self._toolbar(), board, hint], spacing=t.L)

    def _toolbar(self):
        swatches = ft.Row(wrap=True, spacing=t.XS, run_spacing=t.XS, controls=[
            ft.Container(
                ft.Icon(ft.Icons.CHECK, size=16, color=PAPER) if color == self.color else None,
                width=32, height=32, border_radius=16, bgcolor=color, alignment=ft.Alignment.CENTER,
                border=ft.Border.all(2, t.TEXT if color == self.color else t.BORDER),
                on_click=lambda _e, col=color: self._pick(col), tooltip=name)
            for name, color in INKS])
        brush = ft.Row([ft.Icon(ft.Icons.LINE_WEIGHT, size=t.ICON, color=t.MUTED),
                        ft.Slider(value=self.width, min=1, max=18, divisions=17, round=0, label="{value}",
                                  active_color=t.ACCENT, inactive_color=t.TRACK, width=160,
                                  on_change=lambda e: setattr(self, "width", int(e.control.value)),
                                  tooltip="Brush size")], spacing=t.XS)
        actions = ft.Row([
            c.text_button("Undo", self._undo, icon=ft.Icons.UNDO, color=t.TEXT, disabled=not self.strokes),
            c.text_button("Clear", self._clear, icon=ft.Icons.DELETE_OUTLINE, color=t.MUTED, disabled=not self.strokes),
            c.primary_button("Save as image", self._save, icon=ft.Icons.DOWNLOAD, disabled=not self.strokes),
        ], spacing=t.S, wrap=True)
        return c.panel(ft.Row([swatches, brush, ft.Container(expand=True), actions], wrap=True,
                              spacing=t.L, run_spacing=t.M, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                       padding=t.M)

    # ------------------------------- drawing -------------------------------

    def _resized(self, e):
        if e.width:
            self.scale = e.width / BOARD_W
            self._redraw()

    def _board_point(self, e):
        pos = e.local_position
        return (pos.x / self.scale, pos.y / self.scale)

    def _paint(self, stroke):
        return ft.Paint(color=stroke["color"], stroke_width=stroke["width"] * self.scale,
                        stroke_cap=ft.StrokeCap.ROUND, style=ft.PaintingStyle.STROKE)

    def _stroke_shapes(self, stroke):
        s, points = self.scale, stroke["points"]
        if len(points) == 1:
            (x, y), = points
            return [cv.Circle(x * s, y * s, max(1, stroke["width"] / 2) * s,
                              ft.Paint(color=stroke["color"], style=ft.PaintingStyle.FILL))]
        paint = self._paint(stroke)
        return [cv.Line(x0 * s, y0 * s, x1 * s, y1 * s, paint) for (x0, y0), (x1, y1) in zip(points, points[1:])]

    def _shapes(self):
        return [shape for stroke in self.strokes for shape in self._stroke_shapes(stroke)]

    def _redraw(self):
        if self._canvas is not None:
            self._canvas.shapes = self._shapes()
            self._safe_update(self._canvas)

    def _start(self, e):
        first = not self.strokes
        self.strokes.append({"color": self.color, "width": self.width, "points": [self._board_point(e)]})
        if first:
            self.shell.refresh(self)  # enables Undo, Clear and Save
        else:
            self._redraw()

    def _move(self, e):
        if not self.strokes:
            return
        stroke = self.strokes[-1]
        point = self._board_point(e)
        previous = stroke["points"][-1]
        stroke["points"].append(point)
        if len(stroke["points"]) == 2:  # the starting dot becomes a line
            self._canvas.shapes = self._shapes()
        else:
            s = self.scale
            self._canvas.shapes.append(cv.Line(previous[0] * s, previous[1] * s, point[0] * s, point[1] * s,
                                               self._paint(stroke)))
        self._safe_update(self._canvas)

    def _dot(self, e):
        """A tap (no drag) leaves a dot: the same as a stroke with one point."""
        self._start(e)

    @staticmethod
    def _safe_update(control):
        try:
            control.update()
        except Exception:
            pass  # not on screen any more

    # ------------------------------- actions -------------------------------

    def _pick(self, color):
        self.color = color
        self.shell.refresh(self)

    def _undo(self, _e=None):
        if self.strokes:
            self.strokes.pop()
            self.shell.refresh(self)

    def _clear(self, _e=None):
        def wipe():
            self.strokes = []
            self.shell.refresh(self)
        self.shell.confirm("Clear the sketch?", "Everything on the board will be removed.", "Clear", wipe)

    async def _save(self, _e=None):
        if await self.shell.save_file(render_png(self.strokes), "studygenie_sketch.png", "Your sketch"):
            self.core.saved_sketch()


def render_png(strokes):
    """Draws the strokes onto white paper with Pillow and returns PNG bytes."""
    k = EXPORT_SCALE
    image = Image.new("RGB", (BOARD_W * k, BOARD_H * k), PAPER)
    draw = ImageDraw.Draw(image)
    for stroke in strokes:
        width = max(1, round(stroke["width"] * k))
        points = [(x * k, y * k) for x, y in stroke["points"]]
        radius = width / 2
        for x, y in points:  # round ends and joints, like the screen's round caps
            draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=stroke["color"])
        if len(points) > 1:
            draw.line(points, fill=stroke["color"], width=width)
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()
