"""
Covers the command lines that copy.py builds for the external build tools. The arguments
are built by pure functions, so these run without any of the tools being installed.

The expectations follow the command reference that gametextcompiler.exe v1.1 prints when it
is run without arguments, in particular that the LANGUAGE of MERGE_AND_OVERWRITE is
optional and that leaving it out merges the language the loaded files already carry.
"""
import pytest

from generalsmodbuilder.build.copy import (
    BuildFileType, HasCrunchTextureFormat, MakeCrunchArgs, MakeGameTextMergeArgs, MakeW3DExportMode)


EXE = "gametextcompiler.exe"


def MergeArgs(sources: list, target: str, params: dict = None, targetT=None) -> list:
    if targetT == None:
        targetT = BuildFileType.csf if target.endswith(".csf") else BuildFileType.str
    return MakeGameTextMergeArgs(EXE, sources, target, params, targetT)


def test_a_merge_without_a_language_names_no_language():
    # LANGUAGE:None is not a language. The compiler rejects it and writes nothing, so a
    # merge that has no language param must not name one at all.
    args = MergeArgs(["A.str", "B.str"], "Merged.csf")
    assert args == [
        EXE,
        "LOAD_STR(FILE_ID:0,FILE_PATH:A.str)",
        "LOAD_STR(FILE_ID:1,FILE_PATH:B.str)",
        "MERGE_AND_OVERWRITE(FILE_ID:0,FILE_ID:1)",
        "SAVE_CSF(FILE_ID:0,FILE_PATH:Merged.csf)"]
    assert not any("LANGUAGE" in arg for arg in args)


def test_a_merge_with_a_language_names_it_everywhere():
    args = MergeArgs(["A.str", "B.str"], "Merged.csf", {"language": "English"})
    assert args == [
        EXE,
        "LOAD_MULTI_STR(FILE_ID:0,FILE_PATH:A.str,LANGUAGE:English)",
        "LOAD_MULTI_STR(FILE_ID:1,FILE_PATH:B.str,LANGUAGE:English)",
        "MERGE_AND_OVERWRITE(FILE_ID:0,FILE_ID:1,LANGUAGE:English)",
        "SAVE_CSF(FILE_ID:0,FILE_PATH:Merged.csf)"]


def test_a_csf_source_is_loaded_as_a_csf_file():
    # A csf file carries its own language, so it is loaded without one either way.
    args = MergeArgs(["A.str", "B.csf"], "Merged.str", {"language": "German"})
    assert args[1] == "LOAD_MULTI_STR(FILE_ID:0,FILE_PATH:A.str,LANGUAGE:German)"
    assert args[2] == "LOAD_CSF(FILE_ID:1,FILE_PATH:B.csf)"


def test_a_str_target_is_saved_with_its_languages():
    # A csf file stores its language, a str file needs it written out with it.
    assert MergeArgs(["A.str", "B.str"], "Merged.str")[-1] == "SAVE_STR(FILE_ID:0,FILE_PATH:Merged.str)"
    assert MergeArgs(["A.str", "B.str"], "Merged.str", {"language": "Polish"})[-1] == (
        "SAVE_MULTI_STR(FILE_ID:0,FILE_PATH:Merged.str,LANGUAGE:Polish)")


def test_every_later_source_is_merged_over_the_first_slot():
    args = MergeArgs(["A.str", "B.str", "C.str"], "Merged.csf")
    assert "MERGE_AND_OVERWRITE(FILE_ID:0,FILE_ID:1)" in args
    assert "MERGE_AND_OVERWRITE(FILE_ID:0,FILE_ID:2)" in args
    # The first slot is the one that is merged into and is never merged over itself.
    assert "MERGE_AND_OVERWRITE(FILE_ID:0,FILE_ID:0)" not in args


def test_a_single_source_is_loaded_and_saved_without_a_merge():
    args = MergeArgs(["A.str"], "Merged.csf")
    assert args == [EXE, "LOAD_STR(FILE_ID:0,FILE_PATH:A.str)", "SAVE_CSF(FILE_ID:0,FILE_PATH:Merged.csf)"]


def test_swap_and_set_language_runs_before_the_file_is_saved():
    args = MergeArgs(["A.str", "B.str"], "Merged.csf", {"swapAndSetLanguage": "German"})
    assert args[-2] == "SWAP_AND_SET_LANGUAGE(FILE_ID:0,LANGUAGE:German)"
    assert args[-1].startswith("SAVE_CSF")


# The combinations that the patch project exports with, and the two that the exporter has
# no mode for. Hierarchy with animation but no mesh, and animation with mesh but no
# hierarchy, were silently exported as H and as A before, losing what was asked for.
EXPORT_MODES = [
    (True, True, True, "HAM"),
    (True, False, True, "HM"),
    (True, False, False, "H"),
    (False, True, False, "A"),
    (False, False, True, "M"),
]


@pytest.mark.parametrize("hierarchy,animation,mesh,expected", EXPORT_MODES)
def test_an_export_setup_names_its_mode(hierarchy, animation, mesh, expected):
    assert MakeW3DExportMode("Model.blend", hierarchy, animation, mesh) == expected


@pytest.mark.parametrize("hierarchy,animation,mesh", [
    (True, True, False),
    (False, True, True),
    (False, False, False),
])
def test_an_export_setup_without_a_mode_is_reported(hierarchy, animation, mesh):
    with pytest.raises(Exception) as error:
        MakeW3DExportMode("Model.blend", hierarchy, animation, mesh)
    assert "Model.blend" in str(error.value)
    assert "no export mode" in str(error.value)


CRUNCH = "crunch.exe"


def CrunchArgs(params: dict = None, textureFormat: str = "", quiet: bool = False) -> list:
    return MakeCrunchArgs(CRUNCH, "Texture.tga", "Texture.dds", params, textureFormat, quiet)


def test_a_texture_is_written_as_dds_without_progress():
    assert CrunchArgs() == [
        CRUNCH, "-file", "Texture.tga", "-out", "Texture.dds", "-fileformat", "dds", "-noprogress"]


def test_the_params_of_the_build_file_are_passed_on():
    args = CrunchArgs({"-quality": 255, "-mipmode": "Generate"})
    assert args[-4:] == ["-quality", "255", "-mipmode", "Generate"]


def test_a_format_param_without_a_value_stays_a_bare_flag():
    # The patch project writes the format as "-DXT1": "", where the empty value is dropped.
    assert CrunchArgs({"-DXT1": ""})[-1] == "-DXT1"


def test_a_texture_format_is_recognized_in_any_case():
    # crunch reads its arguments in any case, so a format written in lower case is a format
    # and must not have an automatically chosen one appended after it.
    assert HasCrunchTextureFormat({"-DXT1": ""})
    assert HasCrunchTextureFormat({"-dxt5": ""})
    assert HasCrunchTextureFormat({"-DXT5_CCxY": ""})
    assert not HasCrunchTextureFormat({"-quality": 255, "-mipmode": "Generate"})
    assert not HasCrunchTextureFormat({})
    assert not HasCrunchTextureFormat(None)


def test_the_automatic_texture_format_comes_last():
    args = CrunchArgs({"-quality": 255}, textureFormat="-DXT5")
    assert args[-1] == "-DXT5"


def test_quiet_is_asked_for_by_the_caller():
    assert "-quiet" not in CrunchArgs(quiet=False)
    assert "-quiet" in CrunchArgs(quiet=True)


def test_every_known_texture_format_is_recognized():
    from generalsmodbuilder.build.copy import CrunchTextureFormatSet
    for name in CrunchTextureFormatSet:
        assert HasCrunchTextureFormat({name: ""})
        assert HasCrunchTextureFormat({name.lower(): ""})
        assert HasCrunchTextureFormat({name.upper(): ""})
