from tkinter.ttk import Frame
from tkinter import LEFT, RIGHT, BOTH, Y, VERTICAL

from PIL import Image, ImageDraw, ImageTk
from ttkbootstrap import Scrollbar, Treeview

from generalsmodbuilder.gui.theme import AMBER, BACKGROUND, MUTED

CHECK_SIZE = 13

# The mark is drawn at this multiple and scaled down, because Tk has no antialiasing.
_SUPERSAMPLE = 4


def MatchPackSelection(allNames: list[str], wantedNames: list[str]) -> list[int]:
    """The rows to tick, for the pack names that the command line asked to build or install."""
    wanted = set(wantedNames)
    return [index for index, name in enumerate(allNames) if name in wanted]


def DrawCheckImage(size: int, checked: bool) -> Image.Image:
    """
    The check mark of one row, drawn to match the themed check buttons. A glyph from a font
    would be tied to the row font and was too small to read at this size.
    """
    edge = size * _SUPERSAMPLE
    image = Image.new("RGBA", (edge, edge), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    radius = int(edge * 0.18)

    if checked:
        draw.rounded_rectangle([0, 0, edge - 1, edge - 1], radius=radius, fill=AMBER)
        draw.line(
            [(edge * 0.24, edge * 0.52), (edge * 0.43, edge * 0.72), (edge * 0.78, edge * 0.28)],
            fill=BACKGROUND, width=int(_SUPERSAMPLE * 2.0), joint="curve")
    else:
        draw.rounded_rectangle([0, 0, edge - 1, edge - 1], radius=radius, outline=MUTED,
                               width=int(_SUPERSAMPLE * 1.3))

    return image.resize((size, size), Image.LANCZOS)


class PackList:
    """
    The bundle pack list. A tree view rather than a list box, because the theme does not
    reach a classic tk widget, and a click anywhere on a row toggles it as the list box did.
    """

    def __init__(self, parent: Frame):
        self.checkOn = ImageTk.PhotoImage(DrawCheckImage(CHECK_SIZE, True))
        self.checkOff = ImageTk.PhotoImage(DrawCheckImage(CHECK_SIZE, False))
        self.names = dict[str, str]()
        self.checked = dict[str, bool]()

        self.tree = Treeview(parent, show="tree", selectmode="none", style="Flat.Treeview")
        self.tree.column("#0", width=150, stretch=True)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        self.tree.bind("<Button-1>", self._OnClick)

        scrollbar = Scrollbar(parent, orient=VERTICAL, command=self.tree.yview,
                              bootstyle="secondary-round")
        scrollbar.pack(side=RIGHT, fill=Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

    def SetNames(self, names: list[str], checkedNames: list[str]) -> None:
        self.tree.delete(*self.tree.get_children())
        self.names.clear()
        self.checked.clear()

        ticked: list[int] = MatchPackSelection(names, checkedNames)
        for index, name in enumerate(names):
            item: str = self.tree.insert("", "end")
            self.names[item] = name
            self._SetChecked(item, index in ticked)

    def CheckedNames(self) -> list[str]:
        return [self.names[item] for item in self.tree.get_children() if self.checked[item]]

    def Count(self) -> int:
        return len(self.tree.get_children())

    def CheckedCount(self) -> int:
        return len(self.CheckedNames())

    def _SetChecked(self, item: str, checked: bool) -> None:
        self.checked[item] = checked
        self.tree.item(item, text=f" {self.names[item]}",
                       image=self.checkOn if checked else self.checkOff)

    def _OnClick(self, event) -> str:
        item: str = self.tree.identify_row(event.y)
        if item:
            self._SetChecked(item, not self.checked[item])
        # The tree must not take a selection of its own, the check mark is the state.
        return "break"
