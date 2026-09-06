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
    transform.WriteLines(target, transform.TransformLines(transform.ReadLines(source)))
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
