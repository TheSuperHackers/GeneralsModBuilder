import pytest

from generalsmodbuilder.gui.status import (
    ABORTING, IDLE, RUNNING, FormatStatusText, StatusStyle)


@pytest.mark.parametrize("packCount, selectedCount, expected", [
    (6, 2, "Idle — 6 bundle packs, 2 selected"),
    (1, 1, "Idle — 1 bundle pack, 1 selected"),
    (1, 0, "Idle — 1 bundle pack, none selected"),
    (0, 0, "Idle — 0 bundle packs, none selected"),
])
def test_the_idle_text_counts_the_bundle_packs(packCount, selectedCount, expected):
    assert FormatStatusText(IDLE, packCount, selectedCount) == expected


def test_a_running_job_names_what_it_is_doing():
    assert FormatStatusText(RUNNING, 6, 2, "Build") == "Running Build"


def test_an_aborting_job_names_what_it_is_stopping():
    assert FormatStatusText(ABORTING, 6, 2, "Build") == "Aborting Build"


@pytest.mark.parametrize("state, expected", [(RUNNING, "Running"), (ABORTING, "Aborting")])
def test_a_job_without_a_name_still_reads_as_a_sentence(state, expected):
    assert FormatStatusText(state, 6, 2) == expected


def test_an_unknown_state_falls_back_to_idle():
    # The status bar must never be blank, whatever the caller passes.
    assert FormatStatusText("nonsense", 3, 1) == "Idle — 3 bundle packs, 1 selected"


@pytest.mark.parametrize("state, expected", [
    (IDLE, "Ok.TLabel"),
    (RUNNING, "Busy.TLabel"),
    (ABORTING, "Busy.TLabel"),
    ("nonsense", "Ok.TLabel"),
])
def test_the_status_dot_is_coloured_by_state(state, expected):
    assert StatusStyle(state) == expected
