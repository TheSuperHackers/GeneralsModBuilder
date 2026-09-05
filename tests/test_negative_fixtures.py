"""
Mirrors the negative configuration fixtures that the sample project keeps in its
Tests directory, so that this repository proves those rules on its own rather than
relying on a project that lives beside it.
"""
import pytest

from generalsmodbuilder.build.copy import BuildFileType, SupportsMultiSource
from generalsmodbuilder.data.bundles import MakeBundlesFromJsons


def MakeItemJson(jFile: dict) -> dict:
    return {"bundles": {"items": [{"name": "SampleInvalid", "big": True, "files": [jFile]}]}}


def test_empty_multi_source(MakeJsonFile):
    with pytest.raises(AssertionError) as error:
        MakeBundlesFromJsons([MakeJsonFile(MakeItemJson({
            "sourceParent": "Src", "multiSource": [], "target": "Data/Empty.ini"}))])
    assert "multiSource must not be empty" in str(error.value)


def test_missing_target(MakeJsonFile, MakeFile):
    MakeFile("Src/GameLOD_Part1.ini")
    MakeFile("Src/GameLOD_Part2.ini")
    with pytest.raises(AssertionError) as error:
        MakeBundlesFromJsons([MakeJsonFile(MakeItemJson({
            "sourceParent": "Src", "multiSource": ["GameLOD_Part1.ini", "GameLOD_Part2.ini"]}))])
    assert "target is mandatory with 'multiSource'" in str(error.value)


def test_source_and_multi_source(MakeJsonFile, MakeFile):
    MakeFile("Src/GameLOD_Part1.ini")
    MakeFile("Src/GameLOD_Part2.ini")
    with pytest.raises(AssertionError) as error:
        MakeBundlesFromJsons([MakeJsonFile(MakeItemJson({
            "sourceParent": "Src",
            "source": "GameLOD_Part1.ini",
            "multiSource": ["GameLOD_Part2.ini"],
            "target": "Data/Joined.ini"}))])
    assert "cannot specify 'source' and 'multiSource' together" in str(error.value)


def test_wildcard_target(MakeJsonFile, MakeFile):
    MakeFile("Src/GameLOD_Part1.ini")
    with pytest.raises(AssertionError) as error:
        MakeBundlesFromJsons([MakeJsonFile(MakeItemJson({
            "sourceParent": "Src", "multiSource": ["GameLOD_Part1.ini"], "target": "Data/*.ini"}))])
    assert "cannot contain a wildcard with 'multiSource'" in str(error.value)


# The fifth fixture is not a parser rule. Which file types can be combined is decided
# when the files are built, so it is proven against that decision directly.
def test_unsupported_target_type():
    assert not SupportsMultiSource(BuildFileType.tga, BuildFileType.tga)
    assert not SupportsMultiSource(BuildFileType.ini, BuildFileType.tga)
    assert not SupportsMultiSource(BuildFileType.ini, BuildFileType.wnd)


def test_supported_target_types():
    assert SupportsMultiSource(BuildFileType.ini, BuildFileType.ini)
    assert SupportsMultiSource(BuildFileType.wnd, BuildFileType.wnd)
    assert SupportsMultiSource(BuildFileType.str, BuildFileType.str)
    assert SupportsMultiSource(BuildFileType.csf, BuildFileType.str)
    assert SupportsMultiSource(BuildFileType.str, BuildFileType.csf)
    assert SupportsMultiSource(BuildFileType.csf, BuildFileType.csf)
