"""
Mirrors the negative configuration fixtures that the sample project keeps in its
Tests directory, so that this repository proves those rules on its own rather than
relying on a project that lives beside it.
"""
import pytest

from generalsmodbuilder.build.copy import BuildFileType, SupportsMultiSource
from generalsmodbuilder.data.bundles import MakeBundlesFromJsons
from generalsmodbuilder.data.common import KNOWN_BUILD_FILE_PARAM_TYPES


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


def MakeParamsJson(params: dict) -> dict:
    return MakeItemJson({"sourceParent": "Src", "source": "Weapon.ini", "params": params})


def MakeParamsBundles(MakeJsonFile, MakeFile, params: dict):
    MakeFile("Src/Weapon.ini")
    return MakeBundlesFromJsons([MakeJsonFile(MakeParamsJson(params))])


def ExpectParamError(MakeJsonFile, MakeFile, params: dict, expected: str):
    with pytest.raises(AssertionError) as error:
        MakeParamsBundles(MakeJsonFile, MakeFile, params)
    assert "bundles.items.files.params" in str(error.value)
    assert expected in str(error.value)


def test_delete_whitespace_must_be_a_number(MakeJsonFile, MakeFile):
    ExpectParamError(MakeJsonFile, MakeFile, {"deleteWhitespace": 1.0}, "should be a number")


def test_delete_whitespace_must_not_be_a_switch(MakeJsonFile, MakeFile):
    # bool is an int in python, but a count has to be written as a number.
    ExpectParamError(MakeJsonFile, MakeFile, {"deleteWhitespace": True}, "should be a number")


def test_exclude_markers_list_must_be_a_list(MakeJsonFile, MakeFile):
    ExpectParamError(MakeJsonFile, MakeFile, {"excludeMarkersList": ";begin"}, "[begin, end] pairs")


def test_exclude_markers_need_a_begin_and_an_end(MakeJsonFile, MakeFile):
    ExpectParamError(MakeJsonFile, MakeFile, {"excludeMarkersList": [[";begin"]]}, "[begin, end] pairs")


def test_exclude_markers_must_not_be_empty_strings(MakeJsonFile, MakeFile):
    ExpectParamError(MakeJsonFile, MakeFile, {"excludeMarkersList": [["", ""]]}, "[begin, end] pairs")


def test_w3d_flag_must_be_a_bool(MakeJsonFile, MakeFile):
    ExpectParamError(MakeJsonFile, MakeFile, {"w3dExportMesh": "true"}, "true or false")


def test_rescale_must_be_a_number(MakeJsonFile, MakeFile):
    ExpectParamError(MakeJsonFile, MakeFile, {"rescale": "half"}, "one or two numbers")


def test_resize_takes_at_most_two_numbers(MakeJsonFile, MakeFile):
    ExpectParamError(MakeJsonFile, MakeFile, {"resize": [512, 512, 512]}, "one or two numbers")


def test_force_eol_must_be_a_string(MakeJsonFile, MakeFile):
    ExpectParamError(MakeJsonFile, MakeFile, {"forceEOL": 1}, "should be a string")


def test_params_of_the_real_mod_projects_are_accepted(MakeJsonFile, MakeFile):
    # Copied from the patch and the sample project, so that the known param types can never
    # tighten past the data that is actually built with them.
    for params in [
        {"forceEOL": chr(13) + chr(10), "deleteComments": ";", "deleteWhitespace": 1,
         "sourceEncoding": "ascii", "targetEncoding": "ascii",
         "excludeMarkersList": [[";patch104p-optional-begin", ";patch104p-optional-end"]]},
        {"language": "Arabic", "excludeMarkersList": [["//core-begin", "//core-end"]]},
        {"swapAndSetLanguage": "English"},
        {"w3dExportHierarchy": True, "w3dExportAnimation": False, "w3dExportMesh": True},
        {"-quality": 255, "-mipmode": "Generate", "-DXT1": ""},
        {"rescale": 0.5, "resampling": "BICUBIC", "-quality": 255},
        {"resize": [1024, 1024]},
        {"excludeMarkersList": []},
    ]:
        assert MakeParamsBundles(MakeJsonFile, MakeFile, params) != None


def test_a_known_param_is_matched_however_its_table_spells_it():
    # The tables spell a param the way it is meant to be read and are lowered when they are
    # merged, so that a param declared in camel case cannot lose its verification in silence.
    assert all(name == name.lower() for name in KNOWN_BUILD_FILE_PARAM_TYPES)
    assert "w3dcreatetexturexmls" in KNOWN_BUILD_FILE_PARAM_TYPES


def test_a_camel_case_param_declaration_is_still_verified(MakeJsonFile, MakeFile):
    ExpectParamError(MakeJsonFile, MakeFile, {"W3DCreateTextureXmls": 1}, "true or false")


def test_a_param_the_builder_does_not_know_is_left_alone(MakeJsonFile, MakeFile):
    # Build tool arguments are passed on as they are written and must not be verified here.
    assert MakeParamsBundles(MakeJsonFile, MakeFile, {"-someNewCrunchArg": [1, "two"]}) != None
