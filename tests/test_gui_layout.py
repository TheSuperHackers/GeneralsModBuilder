from tkinter.ttk import Frame

import pytest

from conftest import HasHint

from generalsmodbuilder.gui.layout import Section


@pytest.fixture
def MakeSection(Root):
    made = list()

    def Make(trailing: list):
        parent = Frame(Root)
        parent.pack(fill="both", expand=True)
        holder, body, buttons = Section(parent, "Output", trailing=trailing)
        holder.pack(fill="both", expand=True)
        Root.update()
        made.append(parent)
        return holder, body, buttons

    yield Make

    for parent in made:
        parent.destroy()
    Root.update()


def test_every_caption_button_carries_its_hint(MakeSection):
    _, _, buttons = MakeSection(
        [("Clear", lambda: None, "Empties the output pane."),
         ("Copy", lambda: None, "Copies the output to the clipboard.")])

    assert len(buttons) == 2
    for button in buttons:
        assert HasHint(button), button["text"]


def test_the_caption_buttons_read_in_the_order_they_are_given(MappedRoot, MakeSection):
    _, _, buttons = MakeSection(
        [("Clear", lambda: None, "Empties the output pane."),
         ("Copy", lambda: None, "Copies the output to the clipboard.")])

    byName = {button["text"]: button for button in buttons}
    assert byName["Clear"].winfo_x() < byName["Copy"].winfo_x()
