"""StudyGenie's design system: colour, spacing, type, shape, motion and
screen-size breakpoints. Every screen takes its styling from here.

Palette: neutral slate surfaces with one interactive colour (teal). Teal
means "clickable, active, selected, important or progress" and nothing
else. Surfaces are solid; only dialogs get a light glass treatment.

Contrast (WCAG) was measured for every text/surface pair used:
  TEXT   on BG/NAV/SURFACE/ELEVATED: 17.5 / 16.3 / 14.5 / 12.7
  MUTED  on BG/NAV/SURFACE/ELEVATED:  7.5 /  7.0 /  6.2 /  5.4
  ACCENT on BG/NAV/SURFACE/ELEVATED: 10.3 /  9.6 /  8.5 /  7.5
  BG text on ACCENT (primary buttons): 10.3 (13.0 on hover)
  ERROR on SURFACE: 5.7
"""

import flet as ft

# --- Colour: the palette ----------------------------------------------------
BG = "#0B0F14"          # main background
NAV = "#121820"         # sidebar and secondary background
SURFACE = "#1B232E"     # cards and standard surfaces
LINE = "#2B3642"        # borders and dividers
ACCENT = "#2DD4BF"      # the interactive colour: clickable, active, selected, progress
ACCENT_HOVER = "#5EEAD4"
TEXT = "#F1F5F9"        # primary text
MUTED = "#94A3B8"       # secondary text

# --- Colour: derived from the palette ---------------------------------------
ELEVATED = "#232D3A"                            # hovered/selected rows, the one emphasised panel
BAR = "#3A4757"                                 # chart bars that aren't highlighted
BORDER = LINE                                   # edges of surfaces
BORDER_STRONG = "#3A4757"                       # inputs and outlined buttons: a step stronger
HOVER = ft.Colors.with_opacity(0.05, TEXT)      # hover wash on rows and icons
PRESSED = ft.Colors.with_opacity(0.10, TEXT)
FOCUS_RING = ACCENT                             # keyboard focus outline
TRACK = LINE                                    # empty part of progress bars
DISABLED_TEXT = "#64748B"                       # reduced contrast, still legible (3.3:1)
SURFACE_GLASS = SURFACE                         # solid: glass is reserved for dialogs
ELEVATED_GLASS = ELEVATED
DIALOG = ft.Colors.with_opacity(0.97, NAV)      # the subtle glass layer
ERROR = "#F87171"       # status only; always paired with an icon and words
SHADOW = ft.Colors.with_opacity(0.25, "#000000")

# --- Spacing (4-point scale) -----------------------------------------------
XS, S, M, L, XL, XXL = 4, 8, 12, 16, 24, 32

# --- Shape -----------------------------------------------------------------
RADIUS = 10             # cards, inputs, buttons: one radius everywhere
RADIUS_LARGE = 12       # dialogs and the Today's Focus panel
RADIUS_PILL = 999       # chips and progress bars
# --- Type: five sizes, two weights ------------------------------------------
CAPTION, BODY, SUBTITLE, TITLE, DISPLAY = 12, 14, 16, 20, 28
REGULAR, SEMIBOLD = ft.FontWeight.W_400, ft.FontWeight.W_600

# --- Size --------------------------------------------------------------------
ICON = 20               # every icon, except navigation (22)
NAV_ICON = 22
TOUCH = 48              # minimum touch target on phones
CONTENT_MAX = 1200      # the main column never stretches wider than this

# --- Screen-size breakpoints --------------------------------------------------
PHONE_MAX = 640         # below: bottom navigation, single column
TABLET_MAX = 1100       # below: icon rail instead of the full sidebar


def layout_for(width):
    if width < PHONE_MAX:
        return "phone"
    if width < TABLET_MAX:
        return "tablet"
    return "desktop"


# --- Motion --------------------------------------------------------------------
QUICK = 150             # ms: hovers, presses
CALM = 250              # ms: page and progress transitions


def motion(duration):
    """An animation, or None when the learner has turned motion off."""
    return None if REDUCED_MOTION else ft.Animation(duration, ft.AnimationCurve.EASE_OUT)


REDUCED_MOTION = False  # set from Settings (Phase 2); Flet can't read the OS preference


def text(value, size=BODY, color=TEXT, weight=REGULAR, **kwargs):
    return ft.Text(value, size=size, color=color, weight=weight, **kwargs)


def page_theme():
    """The Material theme Flet controls inherit (inputs, menus, scrollbars, focus)."""
    return ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=ACCENT, on_primary=BG, secondary=ACCENT, on_secondary=BG,
            surface=SURFACE, on_surface=TEXT, on_surface_variant=MUTED,
            outline=BORDER_STRONG, error=ERROR, on_error=BG,
            primary_container=ELEVATED, on_primary_container=TEXT,
            secondary_container=ELEVATED, on_secondary_container=TEXT,
        ),
        focus_color=ft.Colors.with_opacity(0.16, TEXT),
        hover_color=HOVER,
        splash_color=PRESSED,
        divider_color=BORDER,
        scrollbar_theme=ft.ScrollbarTheme(
            thickness=6, radius=3, thumb_color=ft.Colors.with_opacity(0.22, TEXT),
            track_visibility=False, thumb_visibility=False, main_axis_margin=2, cross_axis_margin=2,
        ),
        visual_density=ft.VisualDensity.STANDARD,
    )
