import io
import queue

import pytest

from generalsmodbuilder.gui.logpane import (
    ERROR, NORMAL, WARNING, ClassifyLine, LineBuffer, StreamTee)


@pytest.mark.parametrize("line, expected", [
    ("Warning: setup.step is Zero. Exiting.", WARNING),
    ("  Warning: The installed Mod may not work correctly.", WARNING),
    ("WARNING: something", WARNING),
    ("ERROR CALLSTACK", ERROR),
    ("Traceback (most recent call last):", ERROR),
    ("Build bundle pack 'ProjectCore'", NORMAL),
    ("", NORMAL),
    ("  Copy 132 files", NORMAL),
])
def test_a_line_is_classified_by_how_the_builder_writes_it(line, expected):
    assert ClassifyLine(line) == expected


def test_a_word_that_merely_contains_error_is_not_an_error():
    # 'terror' and '0 errors found' must not colour a whole line red.
    assert ClassifyLine("0 errors found") == NORMAL
    assert ClassifyLine("Copy terrorist.tga") == NORMAL


def test_text_without_a_newline_is_held_back():
    buffer = LineBuffer()
    assert buffer.Add("half a line") == []


def test_a_newline_completes_the_held_text():
    buffer = LineBuffer()
    buffer.Add("half a line")
    assert buffer.Add(" and the rest\n") == ["half a line and the rest"]


def test_several_lines_in_one_write_come_out_separately():
    buffer = LineBuffer()
    assert buffer.Add("one\ntwo\nthree\n") == ["one", "two", "three"]


def test_the_text_after_the_last_newline_stays_pending():
    buffer = LineBuffer()
    assert buffer.Add("one\ntwo") == ["one"]
    assert buffer.Add("\n") == ["two"]


def test_print_writes_its_text_and_its_newline_separately():
    # This is what print actually does, and it must still yield exactly one line.
    buffer = LineBuffer()
    assert buffer.Add("a message") == []
    assert buffer.Add("\n") == ["a message"]


def test_flush_hands_out_an_unfinished_line():
    buffer = LineBuffer()
    buffer.Add("no newline yet")
    assert buffer.Flush() == ["no newline yet"]
    assert buffer.Flush() == []


def test_a_tee_writes_to_the_original_stream():
    stream = io.StringIO()
    tee = StreamTee(stream, queue.Queue())
    tee.write("Build bundle pack\n")
    assert stream.getvalue() == "Build bundle pack\n"


def test_a_tee_queues_what_it_writes():
    stream = io.StringIO()
    lines = queue.Queue()
    tee = StreamTee(stream, lines)
    tee.write("one\ntwo\n")
    assert [lines.get_nowait(), lines.get_nowait()] == ["one", "two"]


def test_a_tee_reports_the_length_written_so_print_is_happy():
    tee = StreamTee(io.StringIO(), queue.Queue())
    assert tee.write("four") == 4


def test_a_tee_passes_on_whether_the_console_is_a_terminal():
    # The gui only clears the console when it is one.
    class FakeStream(io.StringIO):
        def isatty(self) -> bool:
            return True

    assert StreamTee(FakeStream(), queue.Queue()).isatty() is True
    assert StreamTee(io.StringIO(), queue.Queue()).isatty() is False
