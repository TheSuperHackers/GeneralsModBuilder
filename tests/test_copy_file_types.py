"""
Covers how a file path is read as a file type.
"""
from generalsmodbuilder.build.copy import (
    BuildFileType, BuildFileTypeMarkers, FileTypeStringDict, GetFileType)


def test_an_extension_names_its_file_type():
    assert GetFileType("Data/INI/Weapon.ini") == BuildFileType.ini
    assert GetFileType("Art/Texture.dds") == BuildFileType.dds
    assert GetFileType("Art/Model.w3d") == BuildFileType.w3d


def test_an_extension_is_read_in_any_case():
    assert GetFileType("Data/INI/Weapon.INI") == BuildFileType.ini
    assert GetFileType("Art/Texture.Dds") == BuildFileType.dds


def test_both_tiff_spellings_name_the_same_type():
    assert GetFileType("Art/Texture.tif") == BuildFileType.tiff
    assert GetFileType("Art/Texture.tiff") == BuildFileType.tiff


def test_an_unknown_extension_is_any():
    assert GetFileType("Audio/Sound.wav") == BuildFileType.Any
    assert GetFileType("Art/Cursor.ani") == BuildFileType.Any
    assert GetFileType("Data/NoExtension") == BuildFileType.Any
    assert GetFileType("Data/Trailing.") == BuildFileType.Any


def test_a_marker_is_never_read_from_an_extension():
    # Any and Auto are markers and not file types. A file that happens to be named after
    # one of them is an unknown extension like any other.
    assert GetFileType("Data/File.any") == BuildFileType.Any
    assert GetFileType("Data/File.Any") == BuildFileType.Any
    assert GetFileType("Data/File.auto") == BuildFileType.Any
    assert GetFileType("Data/File.AUTO") == BuildFileType.Any


def test_the_extension_map_holds_no_marker():
    for marker in BuildFileTypeMarkers:
        assert marker.name.lower() not in FileTypeStringDict
        assert marker not in FileTypeStringDict.values()


def test_every_file_type_is_reachable_by_its_name():
    for fileType in BuildFileType:
        if fileType not in BuildFileTypeMarkers:
            assert GetFileType("File." + fileType.name) == fileType
