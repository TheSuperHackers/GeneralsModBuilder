"""
Covers TextTransform, which applies the text params of a bundle file to the lines of a
text file. The params are read from json, so the cases here are written the way a mod
project writes them.
"""
import io

from generalsmodbuilder.build.copy import TextTransform


CR = chr(13)
LF = chr(10)
CRLF = CR + LF


def MakeTextFile(tmp_path, name: str, text: str) -> str:
    """
    Writes a source file byte for byte, so that a test states the line endings it is about.
    """
    path = tmp_path / name
    with io.open(str(path), "w", encoding="ascii", newline="") as wfile:
        wfile.write(text)
    return str(path)


def ReadBytes(path: str) -> str:
    with io.open(path, "r", encoding="ascii", newline="") as rfile:
        return rfile.read()


def Apply(tmp_path, text: str, params: dict, name: str = "Source.ini") -> str:
    """
    Runs the whole read, transform and write cycle and returns the target file as written.
    """
    source = MakeTextFile(tmp_path, name, text)
    target = str(tmp_path / ("Target_" + name))
    transform = TextTransform(params)
    transform.WriteLines(target, transform.TransformLines(transform.ReadLines(source), [source]))
    return ReadBytes(target)


def test_line_endings_are_kept_when_no_param_asks_for_another_one(tmp_path):
    # Only the encoding is named, so the line endings must come out as they went in.
    text = "GameData" + CRLF + "  Value = 1" + CRLF + "End" + CRLF
    assert Apply(tmp_path, text, {"targetEncoding": "ascii"}) == text


def test_force_eol_replaces_every_line_ending(tmp_path):
    text = "One" + LF + "Two" + LF
    assert Apply(tmp_path, text, {"forceEOL": CRLF}) == "One" + CRLF + "Two" + CRLF


def test_force_eol_converts_crlf_to_lf(tmp_path):
    text = "One" + CRLF + "Two" + CRLF
    assert Apply(tmp_path, text, {"forceEOL": LF}) == "One" + LF + "Two" + LF


def test_mixed_line_endings_are_each_kept(tmp_path):
    text = "One" + CRLF + "Two" + LF + "Three" + CRLF
    assert Apply(tmp_path, text, {"deleteComments": ";"}) == text


def test_last_line_without_an_ending_is_given_the_one_before_it(tmp_path):
    # An unterminated last line must not end the file in an ending foreign to it, and must
    # not merge into the first line of the next file when several files are appended.
    text = "One" + CRLF + "Two"
    assert Apply(tmp_path, text, {"targetEncoding": "ascii"}) == "One" + CRLF + "Two" + CRLF


def test_single_unterminated_line_ends_in_lf(tmp_path):
    assert Apply(tmp_path, "Only", {"targetEncoding": "ascii"}) == "Only" + LF


def test_comments_are_deleted_without_touching_the_line_ending(tmp_path):
    text = "Value = 1 ; a comment" + CRLF + "; a whole line" + CRLF
    assert Apply(tmp_path, text, {"deleteComments": ";"}) == "Value = 1 " + CRLF + "" + CRLF


def test_delete_whitespace_collapses_spaces_and_drops_empty_lines(tmp_path):
    text = "  Value   =    1  " + CRLF + "   " + CRLF + "End" + CRLF
    assert Apply(tmp_path, text, {"deleteWhitespace": 1}) == "Value = 1" + CRLF + "End" + CRLF


def test_source_and_target_encoding_are_used(tmp_path):
    path = tmp_path / "Latin.ini"
    with io.open(str(path), "w", encoding="cp1252", newline="") as wfile:
        wfile.write("Name = Fahrzeug" + chr(228) + CRLF)

    target = str(tmp_path / "Target.ini")
    transform = TextTransform({"sourceEncoding": "cp1252", "targetEncoding": "utf-8"})
    transform.WriteLines(target, transform.TransformLines(transform.ReadLines(str(path))))

    with io.open(target, "r", encoding="utf-8", newline="") as rfile:
        assert rfile.read() == "Name = Fahrzeug" + chr(228) + CRLF


def test_is_required_only_for_params_that_change_the_text():
    assert not TextTransform({}).IsRequired()
    assert not TextTransform(None).IsRequired()
    assert not TextTransform({"language": "English"}).IsRequired()
    assert TextTransform({"forceEOL": CRLF}).IsRequired()
    assert TextTransform({"deleteComments": ";"}).IsRequired()
    assert TextTransform({"deleteWhitespace": 1}).IsRequired()
    assert TextTransform({"sourceEncoding": "ascii"}).IsRequired()
    assert TextTransform({"targetEncoding": "ascii"}).IsRequired()
    assert TextTransform({"excludeMarkersList": [[";begin", ";end"]]}).IsRequired()


def test_params_are_read_case_insensitively():
    # A mod project may spell a param name in any case, as CaseInsensitiveDict allows.
    transform = TextTransform({"FORCEEOL": CRLF, "DeleteComments": ";"})
    assert transform.forceEOL == CRLF
    assert transform.deleteComments == ";"


BEGIN = ";begin-exclusion-marker"
END = ";end-exclusion-marker"
MARKERS = {"excludeMarkersList": [[BEGIN, END]]}


def test_marked_region_is_removed_with_its_begin_and_end_lines(tmp_path):
    text = ("Keep = 1" + CRLF +
            BEGIN + CRLF +
            "Drop = 1" + CRLF +
            END + CRLF +
            "Keep = 2" + CRLF)
    assert Apply(tmp_path, text, MARKERS) == "Keep = 1" + CRLF + "Keep = 2" + CRLF


def test_marker_pair_on_one_line_removes_that_line(tmp_path):
    # The whole region is on this line, so the line is inside it and must go.
    text = "Keep = 1" + CRLF + BEGIN + " Drop = 1 " + END + CRLF + "Keep = 2" + CRLF
    assert Apply(tmp_path, text, MARKERS) == "Keep = 1" + CRLF + "Keep = 2" + CRLF


def test_same_marker_can_open_again_inside_itself(tmp_path):
    text = ("Keep = 1" + CRLF +
            BEGIN + CRLF + "Drop = 1" + CRLF +
            BEGIN + CRLF + "Drop = 2" + CRLF + END + CRLF +
            "Drop = 3" + CRLF + END + CRLF +
            "Keep = 2" + CRLF)
    assert Apply(tmp_path, text, MARKERS) == "Keep = 1" + CRLF + "Keep = 2" + CRLF


def test_two_marker_pairs_are_filtered_independently(tmp_path):
    params = {"excludeMarkersList": [[BEGIN, END], [";core-begin", ";core-end"]]}
    text = ("Keep = 1" + CRLF +
            BEGIN + CRLF + "Drop = 1" + CRLF + END + CRLF +
            ";core-begin" + CRLF + "Drop = 2" + CRLF + ";core-end" + CRLF +
            "Keep = 2" + CRLF)
    assert Apply(tmp_path, text, params) == "Keep = 1" + CRLF + "Keep = 2" + CRLF


def test_close_without_open_is_reported(tmp_path):
    text = "Keep = 1" + CRLF + END + CRLF
    try:
        Apply(tmp_path, text, MARKERS)
    except AssertionError as error:
        assert "was never opened" in str(error)
        assert END in str(error)
        assert "Source.ini" in str(error)
    else:
        raise AssertionError("a close without an open must be reported")


def test_open_without_close_is_reported(tmp_path):
    # An unclosed marker would otherwise swallow the rest of the text in silence.
    text = "Keep = 1" + CRLF + BEGIN + CRLF + "Drop = 1" + CRLF
    try:
        Apply(tmp_path, text, MARKERS)
    except AssertionError as error:
        assert "without closing it" in str(error)
        assert BEGIN in str(error)
    else:
        raise AssertionError("an open without a close must be reported")


def test_empty_marker_list_changes_nothing(tmp_path):
    text = "Keep = 1" + CRLF
    assert Apply(tmp_path, text, {"excludeMarkersList": [], "targetEncoding": "ascii"}) == text


def test_region_may_open_in_one_source_file_and_close_in_the_next(tmp_path):
    # The sample project relies on this: a multi source ini opens the marker in the first
    # part and closes it in the second, so the balance is over all source files together.
    first = MakeTextFile(tmp_path, "10_First.ini", "Keep = 1" + CRLF + BEGIN + CRLF + "Drop = 1" + CRLF)
    second = MakeTextFile(tmp_path, "20_Second.ini", "Drop = 2" + CRLF + END + CRLF + "Keep = 2" + CRLF)
    target = str(tmp_path / "Joined.ini")

    transform = TextTransform(MARKERS)
    lines = transform.ReadLines(first) + transform.ReadLines(second)
    transform.WriteLines(target, transform.TransformLines(lines, [first, second]))

    assert ReadBytes(target) == "Keep = 1" + CRLF + "Keep = 2" + CRLF


def test_a_bad_marker_names_every_source_file(tmp_path):
    first = MakeTextFile(tmp_path, "First.ini", "Keep = 1" + CRLF)
    second = MakeTextFile(tmp_path, "Second.ini", END + CRLF)

    transform = TextTransform(MARKERS)
    lines = transform.ReadLines(first) + transform.ReadLines(second)
    try:
        transform.TransformLines(lines, [first, second])
    except AssertionError as error:
        assert "First.ini" in str(error) and "Second.ini" in str(error)
    else:
        raise AssertionError("a bad marker must be reported")
