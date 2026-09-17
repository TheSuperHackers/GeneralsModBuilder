import ctypes
from typing import Callable
from tkinter.ttk import Frame, Label

from ttkbootstrap import Button

from generalsmodbuilder.gui.theme import QUIET_STYLE, SMALL_BUTTON_PADDING

MARGIN = 8
GAP = 8
INNER_PADDING = 6
CAPTION_HEIGHT = 25


def EnableDpiAwareness() -> None:
    """
    Must run before the first window is made. Windows otherwise scales the window up as a
    bitmap on a display above 100%, which blurs every glyph in it.
    """
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def Caption(parent, title: str, trailing: list = None) -> tuple[Frame, list[Button]]:
    """
    The caption above a framed box. Its height is fixed so that a caption carrying buttons
    lines up with the plain captions of the boxes beside it.
    """
    caption = Frame(parent, height=CAPTION_HEIGHT)
    caption.pack(fill="x", pady=(0, 3))
    caption.pack_propagate(False)
    Label(caption, text=title.upper(), style="Heading.TLabel").pack(side="left", fill="y")

    buttons = list[Button]()
    text: str
    command: Callable
    for text, command in reversed(trailing or []):
        button = Button(caption, text=text, command=command,
                        bootstyle=QUIET_STYLE, padding=SMALL_BUTTON_PADDING)
        button.pack(side="right", padx=(4, 0))
        buttons.append(button)

    return caption, buttons


def Surface(parent, pad: int = INNER_PADDING) -> tuple[Frame, Frame]:
    """
    One framed box, and the only one the gui uses. The border is the single pixel of the
    outer frame that the inset inner frame leaves showing. A ttk frame carries it because
    a classic tk frame does not paint its background under Tk 9.
    """
    outer = Frame(parent, style="Edge.TFrame")
    inner = Frame(outer, padding=pad)
    inner.pack(fill="both", expand=True, padx=1, pady=1)
    return outer, inner


def Section(parent, title: str, pad: int = INNER_PADDING,
            trailing: list = None) -> tuple[Frame, Frame, list[Button]]:
    """A captioned box. The caller places the holder and fills the body."""
    holder = Frame(parent)
    _, buttons = Caption(holder, title, trailing)
    outer, body = Surface(holder, pad)
    outer.pack(fill="both", expand=True)
    return holder, body, buttons
