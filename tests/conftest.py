import json
import os

import pytest

from generalsmodbuilder.util import JsonFile


@pytest.fixture
def MakeJsonFile(tmp_path):
    """
    Writes a json document to a temporary file and returns it as the JsonFile that the
    parsers take, so that a test can state the json it is about inline.
    """
    def Make(data: dict, name: str = "Test.json") -> JsonFile:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        return JsonFile(str(path))
    return Make


@pytest.fixture
def MakeFile(tmp_path):
    """
    Creates a file below the temporary directory and returns its absolute path, for the
    checks that require a source or script to exist on disk.
    """
    def Make(relPath: str, text: str = "") -> str:
        path = tmp_path / relPath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return str(path)
    return Make


def HasHint(widget) -> bool:
    """Whether a Tooltip is attached, seen through the binding that shows it."""
    return bool(widget.bind("<Enter>"))


def WidgetsOfClass(parent, className: str) -> list:
    """Every widget of the given Tk class below the parent, the parent itself included."""
    found = list()
    if parent.winfo_class() == className:
        found.append(parent)
    for child in parent.winfo_children():
        found.extend(WidgetsOfClass(child, className))
    return found


@pytest.fixture(scope="session")
def Root():
    """
    One hidden window for the whole session. ttkbootstrap binds its Style to the first root,
    so a second one in the same session would talk to an interpreter that is already gone.
    Skips where there is no display, as on a headless runner.
    """
    tk = pytest.importorskip("tkinter")

    try:
        root = tk.Tk()
    except tk.TclError as error:
        pytest.skip(f"no display: {error}")

    from generalsmodbuilder.gui.theme import ApplyTheme

    root.withdraw()
    ApplyTheme(root)
    yield root
    root.destroy()


@pytest.fixture
def MakeButton(Root):
    from ttkbootstrap import Button

    made = list()

    def Make(state: str = "normal"):
        button = Button(Root, text="Abort")
        button["state"] = state
        button.pack()
        Root.update()
        made.append(button)
        return button

    yield Make

    for button in made:
        button.destroy()
    Root.update()


@pytest.fixture
def MappedRoot(Root):
    """The shared root, on screen for the length of one test. Tk delivers a key event only
    to a window that is mapped."""
    Root.deiconify()
    Root.update()
    yield Root
    Root.withdraw()
    Root.update()


@pytest.fixture
def MakeGuiWindow(Root):
    """
    Builds the whole gui into a frame of the shared root, without the main loop, the work
    thread or the redirected streams that Gui.RunWithConfig puts around it.
    """
    from tkinter.ttk import Frame

    from generalsmodbuilder.data.runner import UserRunner
    from generalsmodbuilder.gui.gui import Gui
    from generalsmodbuilder.gui.operations import OPERATIONS

    made = list()

    def Make(initialSequence: dict = None, settings: UserRunner = None):
        holder = Frame(Root)
        holder.pack(fill="both", expand=True)

        gui = Gui()
        gui.configPaths = list()
        gui.buildAndInstallList = list()
        gui._CreateMainWindowVariables(
            holder,
            initialSequence if initialSequence != None else {op.runKwarg: False for op in OPERATIONS},
            printConfig=False,
            verboseLogging=False,
            multiProcessing=False,
            settings=settings if settings != None else UserRunner())
        gui._CreateMainWindowElements(holder)
        Root.update()

        made.append(holder)
        return gui, holder

    yield Make

    for holder in made:
        holder.destroy()
    Root.update()
