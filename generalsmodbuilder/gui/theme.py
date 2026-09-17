from tkinter import Tk

from ttkbootstrap.style import Style, ThemeDefinition


# The five colours of the mod builder palette.
AMBER = "#FFA32B"
KHAKI = "#B29D75"
SAND = "#DCBA71"
TEAL = "#188CA3"
EMBER = "#FC4F0C"

BACKGROUND = "#191715"
FOREGROUND = "#EDE6DA"
BORDER = "#3A342B"
FIELD = "#231F1A"
MUTED = "#9A9086"
SHADE = "#1F1C18"
ACTIVE = "#2A251F"

THEME_NAME = "generals"

# The palette is only legible on a dark background, so the gui has no light mode.
THEME_COLORS: dict[str, str] = {
    "primary": AMBER,
    "secondary": KHAKI,
    "success": SAND,
    "info": TEAL,
    "warning": AMBER,
    "danger": EMBER,
    "light": KHAKI,
    "dark": SHADE,
    "bg": BACKGROUND,
    "fg": FOREGROUND,
    "selectbg": TEAL,
    "selectfg": "#FFFFFF",
    "border": BORDER,
    "inputfg": FOREGROUND,
    "inputbg": FIELD,
    "active": ACTIVE,
}

FONT = ("Segoe UI", 10)
FONT_HEADING = ("Segoe UI Semibold", 9)
FONT_TITLE = ("Segoe UI Semibold", 13)
FONT_MONO = ("Cascadia Mono", 9)

BUTTON_PADDING = (6, 2)
SMALL_BUTTON_PADDING = (6, 1)
TREE_ROW_HEIGHT = 20

# Every button that runs something is an amber outline, filling amber under the pointer.
ACTION_STYLE = "warning-outline"
QUIET_STYLE = "secondary-outline"


def ApplyTheme(window: Tk) -> Style:
    """Registers the mod builder theme, selects it and configures the named styles."""
    style = Style()
    style.register_theme(ThemeDefinition(name=THEME_NAME, colors=THEME_COLORS, mode="dark"))
    style.theme_use(THEME_NAME)
    _ConfigureStyles(style)
    window.configure(bg=BACKGROUND)
    return style


def _ConfigureStyles(style: Style) -> None:
    style.configure(".", font=FONT)
    style.configure("TButton", font=FONT, padding=BUTTON_PADDING)
    style.configure("TCheckbutton", font=FONT, padding=0)
    style.configure("TEntry", padding=2)

    # A framed box is a frame in the border colour with its content inset by one pixel.
    # A ttk frame is used because a tk frame does not paint its background under Tk 9.
    style.configure("Edge.TFrame", background=BORDER)

    style.configure("Heading.TLabel", font=FONT_HEADING, foreground=SAND)
    style.configure("Title.TLabel", font=FONT_TITLE, foreground=AMBER)
    style.configure("Dim.TLabel", font=FONT, foreground=MUTED)
    style.configure("Ok.TLabel", font=FONT, foreground=TEAL)
    style.configure("Busy.TLabel", font=FONT, foreground=AMBER)

    # The sash otherwise draws a bright handle in the middle of the divider.
    style.configure("TPanedwindow", background=BACKGROUND)
    style.configure("Sash", gripcount=0, background=BACKGROUND, bordercolor=BACKGROUND,
                    lightcolor=BACKGROUND, darkcolor=BACKGROUND, handlesize=0, handlepad=0)

    # Drop the field and the expander, so that the surface draws the only border and the
    # rows of a flat list do not reserve room for children they never have.
    style.layout("Flat.Treeview", [("Treeview.padding", {"sticky": "nswe", "children": [
        ("Treeview.treearea", {"sticky": "nswe"})]})])
    style.layout("Flat.Treeview.Item", [("Treeitem.padding", {"sticky": "nswe", "children": [
        ("Treeitem.image", {"side": "left", "sticky": ""}),
        ("Treeitem.text", {"sticky": "nswe"})]})])
    style.configure("Flat.Treeview", font=FONT, rowheight=TREE_ROW_HEIGHT,
                    background=FIELD, fieldbackground=FIELD, borderwidth=0)
