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
