import pytest

from generalsmodbuilder import util


def MakeContext() -> util.JsonContext:
    return util.JsonContext("ModBundleItems.json")


def test_path_is_built_while_descending():
    ctx = MakeContext().Sub("bundles").Sub("items").At(3, "GameFiles").Sub("files").At(2)
    assert ctx.Name("target") == "ModBundleItems.json: bundles.items[3] 'GameFiles'.files[2].target"
    assert ctx.Name() == "ModBundleItems.json: bundles.items[3] 'GameFiles'.files[2]"


def test_element_without_a_name_is_named_by_index_alone():
    assert MakeContext().Sub("packs").At(0).Name() == "ModBundleItems.json: packs[0]"


def test_optional_key_returns_the_default_when_absent():
    ctx = MakeContext().Sub("bundles")
    assert ctx.GetOptional({}, "itemsPrefix", str, default="") == ""
    assert ctx.GetOptional({}, "big", bool, default=True) is True
    assert ctx.GetOptional({"itemsPrefix": "001_"}, "itemsPrefix", str, default="") == "001_"


def test_mandatory_key_fails_when_absent():
    ctx = MakeContext().Sub("bundles").Sub("items").At(0)
    with pytest.raises(AssertionError) as error:
        ctx.GetMandatory({}, "name", str)
    assert str(error.value) == "ModBundleItems.json: bundles.items[0].name is required but is not set"


def test_bad_type_names_the_file_the_section_and_the_key():
    ctx = MakeContext().Sub("bundles").Sub("items").At(3, "GameFiles").Sub("files").At(2)
    with pytest.raises(AssertionError) as error:
        ctx.GetOptional({"target": 1}, "target", str)
    assert str(error.value) == (
        "ModBundleItems.json: bundles.items[3] 'GameFiles'.files[2].target "
        "is type:int but should be type:str")


def test_element_type_is_verified_with_the_element_index():
    ctx = MakeContext().Sub("bundles").Sub("packs").At(0, "Core")
    assert ctx.GetMandatory({"itemNames": ["A", "B"]}, "itemNames", list, elementType=str) == ["A", "B"]
    with pytest.raises(AssertionError) as error:
        ctx.GetMandatory({"itemNames": ["A", 2]}, "itemNames", list, elementType=str)
    assert str(error.value) == (
        "ModBundleItems.json: bundles.packs[0] 'Core'.itemNames[1] "
        "is type:int but should be type:str")


def test_verify_names_the_place_and_the_key():
    ctx = MakeContext().Sub("folders")
    ctx.Verify(True, "must differ")
    with pytest.raises(AssertionError) as error:
        ctx.Verify(False, "must not equal buildDir", key="releaseDir")
    assert str(error.value) == "ModBundleItems.json: folders.releaseDir must not equal buildDir"


def test_union_and_tuple_expected_types_are_reported():
    ctx = MakeContext().Sub("tools")
    with pytest.raises(AssertionError) as error:
        ctx.GetOptional({"version": []}, "version", (int, float))
    assert "but should be type:int or float" in str(error.value)
