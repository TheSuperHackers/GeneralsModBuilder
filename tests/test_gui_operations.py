import dataclasses
import inspect

import pytest

from generalsmodbuilder.buildfunctions import RunWithConfig
from generalsmodbuilder.gui.operations import OPERATIONS


def test_the_operations_appear_in_the_order_the_gui_shows_them():
    assert [op.label for op in OPERATIONS] == [
        "Make Change Log",
        "Clean",
        "Build",
        "Build Release",
        "Install",
        "Run Game",
        "Uninstall",
    ]


def test_every_run_keyword_is_a_boolean_switch_of_the_build_function():
    # This is what catches a renamed parameter of RunWithConfig, which would otherwise
    # only show up as a TypeError once the button is pressed.
    params = inspect.signature(RunWithConfig).parameters
    for op in OPERATIONS:
        assert op.runKwarg in params, op.label
        assert params[op.runKwarg].annotation is bool
        assert params[op.runKwarg].default is False


def test_the_run_keywords_are_unique():
    keywords = [op.runKwarg for op in OPERATIONS]
    assert len(set(keywords)) == len(keywords)


def test_the_labels_are_unique_and_not_empty():
    labels = [op.label for op in OPERATIONS]
    assert all(label.strip() for label in labels)
    assert len(set(labels)) == len(labels)


def test_only_the_change_log_runs_without_the_build_context():
    without = [op.runKwarg for op in OPERATIONS if not op.usesBuildContext]
    assert without == ["makeChangeLog"]


def test_an_operation_cannot_be_modified_after_definition():
    # The table is shared by both columns, so a widget must not be able to rewrite it.
    with pytest.raises(dataclasses.FrozenInstanceError):
        OPERATIONS[0].label = "Changed"


def test_every_operation_says_what_it_does():
    hints = [op.hint for op in OPERATIONS]
    assert all(hint.strip() for hint in hints)
    assert len(set(hints)) == len(hints)


def test_a_hint_is_one_short_sentence():
    # It is shown in a one line tooltip, which does not wrap.
    for op in OPERATIONS:
        assert "\n" not in op.hint, op.label
        assert len(op.hint) <= 90, op.label
        assert op.hint.endswith("."), op.label
