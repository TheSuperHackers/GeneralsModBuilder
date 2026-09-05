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
