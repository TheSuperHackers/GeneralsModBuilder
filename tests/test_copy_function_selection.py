"""
Covers which copy function, and therefore which build tool, a source and target file pair
resolves to. GetRequiredToolName is the seam: it selects the same function that a copy
would use, without touching a file and without running a tool.
"""
import pytest

from generalsmodbuilder.build.copy import BuildCopy
from generalsmodbuilder.data.tools import ToolsT


def RequiredTool(source: str, target: str, params: dict = None) -> str:
    return BuildCopy(tools=ToolsT()).GetRequiredToolName([source], target, params)


def RequiredToolOfMulti(sources: list, target: str, params: dict = None) -> str:
    return BuildCopy(tools=ToolsT()).GetRequiredToolName(sources, target, params)


# Every source and target pair that the patch project and the sample project build with,
# so that a change to the selection cannot silently drop one of them.
PAIRS_IN_USE = [
    ("Art/Model.blend", "Art/Model.w3d", "blender"),
    ("Art/Texture.psd", "Art/Texture.dds", "crunch"),
    ("Art/Texture.tga", "Art/Texture.dds", "crunch"),
    ("Art/Texture.tif", "Art/Texture.dds", "crunch"),
    ("Art/Texture.psd", "Art/Texture.tga", None),
    ("Art/Texture.tif", "Art/Texture.tga", None),
    ("Art/Texture.psd", "Art/Texture.bmp", None),
    ("Art/Texture.tga", "Art/Texture.bmp", None),
    ("Data/English/generals.str", "Data/English/generals.csf", "gametextcompiler"),
    ("Data/INI/Weapon.ini", "Data/INI/Weapon.ini", None),
    ("Window/InGameChat.wnd", "Window/InGameChat.wnd", None),
    ("Data/generals.str", "Data/generals.str", None),
    ("Art/Model.w3d", "Art/Model.w3d", None),
    ("Art/Texture.tga", "Art/Texture.tga", None),
    ("Art/Texture.dds", "Art/Texture.dds", None),
    ("Audio/Sound.wav", "Audio/Sound.wav", None),
    ("Art/Cursor.ani", "Art/Cursor.ani", None),
    ("Data/NoExtension", "Data/NoExtension", None),
]


@pytest.mark.parametrize("source,target,tool", PAIRS_IN_USE)
def test_every_pair_in_use_resolves_to_its_tool(source, target, tool):
    assert RequiredTool(source, target) == tool


# Pairs that no rule covers. Each of these was copied byte for byte into a file carrying the
# target extension before, and the build reported success.
PAIRS_WITHOUT_A_CONVERSION = [
    ("Art/Texture.bmp", "Art/Texture.dds"),
    ("Art/Texture.png", "Art/Texture.tga"),
    ("Art/Texture.dds", "Art/Texture.tga"),
    ("Data/INI/Weapon.ini", "Data/English/generals.csf"),
    ("Art/Model.max", "Art/Model.w3d"),
]


@pytest.mark.parametrize("source,target", PAIRS_WITHOUT_A_CONVERSION)
def test_a_pair_without_a_conversion_is_reported(source, target):
    with pytest.raises(Exception) as error:
        RequiredTool(source, target)
    assert source in str(error.value)
    assert target in str(error.value)
    assert "no conversion" in str(error.value)


def test_an_unknown_target_type_is_copied():
    # The builder has no rule for a file type it does not know, so it copies it as it is.
    assert RequiredTool("Data/Notes.txt", "Data/Notes.txt") == None
    assert RequiredTool("Data/Readme.md", "Data/Readme.txt") == None


def test_a_csf_source_builds_a_str_target():
    assert RequiredTool("Data/generals.csf", "Data/generals.str") == "gametextcompiler"


def test_a_dds_file_is_only_compressed_again_for_a_texture_param():
    source, target = "Art/Texture.dds", "Art/Texture.dds"
    # The params of a json entry are shared by every file that the entry builds, so a param
    # that says nothing about textures must leave an already compressed dds alone.
    assert RequiredTool(source, target) == None
    assert RequiredTool(source, target, {}) == None
    assert RequiredTool(source, target, {"forceEOL": chr(13) + chr(10)}) == None
    assert RequiredTool(source, target, {"language": "English"}) == None
    # These do ask for texture work.
    assert RequiredTool(source, target, {"-quality": 255}) == "crunch"
    assert RequiredTool(source, target, {"-mipmode": "Generate"}) == "crunch"
    assert RequiredTool(source, target, {"rescale": 0.5}) == "crunch"
    assert RequiredTool(source, target, {"resize": [512, 512]}) == "crunch"
    assert RequiredTool(source, target, {"resampling": "BICUBIC"}) == "crunch"


def test_a_texture_conversion_needs_crunch_with_or_without_params():
    # A dds built from another file type is always crunched, params or not.
    assert RequiredTool("Art/Texture.tga", "Art/Texture.dds") == "crunch"
    assert RequiredTool("Art/Texture.tga", "Art/Texture.dds", {"-quality": 255}) == "crunch"


def test_multi_source_text_files_are_appended_without_a_tool():
    assert RequiredToolOfMulti(["A.ini", "B.ini"], "Joined.ini") == None
    assert RequiredToolOfMulti(["A.wnd", "B.wnd"], "Joined.wnd") == None
    assert RequiredToolOfMulti(["A.str", "B.str"], "Joined.str") == None


def test_multi_source_game_text_files_are_merged_by_the_tool():
    # A csf source has to become text before it can merge, which only the tool can do.
    assert RequiredToolOfMulti(["A.str", "B.csf"], "Joined.str") == "gametextcompiler"
    assert RequiredToolOfMulti(["A.str", "B.str"], "Joined.csf") == "gametextcompiler"
    assert RequiredToolOfMulti(["A.csf", "B.csf"], "Joined.csf") == "gametextcompiler"


def test_a_target_that_cannot_be_combined_is_reported():
    with pytest.raises(Exception) as error:
        RequiredToolOfMulti(["A.ini", "B.ini"], "Art/Joined.tga")
    assert "Art/Joined.tga" in str(error.value)
    assert "multiple source files" in str(error.value)
