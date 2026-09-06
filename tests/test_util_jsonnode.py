import pytest

from generalsmodbuilder import util


def MakeNode(data: dict) -> util.JsonNode:
    return util.JsonNode("ModBundleItems.json", data)


def MakeItemsNode() -> util.JsonNode:
    data = {"bundles": {"items": [
        {"name": "Other"},
        {"name": "Other"},
        {"name": "Other"},
        {"name": "GameFiles", "files": [{}, {}, {"target": 1}]},
    ]}}
    return MakeNode(data).SubOptional("bundles")


def test_path_is_built_while_descending():
    itemNode = MakeItemsNode().Elements("items", dict, nameKey="name")[3]
    fileNode = itemNode.Elements("files", dict)[2]
    assert fileNode.Name("target") == "ModBundleItems.json: bundles.items[3] 'GameFiles'.files[2].target"
    assert fileNode.Name() == "ModBundleItems.json: bundles.items[3] 'GameFiles'.files[2]"


def test_element_without_a_name_is_named_by_index_alone():
    node = MakeNode({"packs": [{"itemNames": []}]})
    assert node.Elements("packs", dict)[0].Name() == "ModBundleItems.json: packs[0]"


def test_element_whose_name_is_not_a_string_is_named_by_index_alone():
    # The bad name is reported where it is read. Naming the place must not fail first.
    node = MakeNode({"tools": {"list": [{"name": 1}]}}).SubOptional("tools")
    assert node.Elements("list", dict, nameKey="name")[0].Name() == "ModBundleItems.json: tools.list[0]"


def test_optional_key_returns_the_default_when_absent():
    node = MakeNode({"bundles": {"itemsPrefix": "001_"}}).SubOptional("bundles")
    assert node.GetOptional("packsPrefix", str, default="") == ""
    assert node.GetOptional("big", bool, default=True) is True
    assert node.GetOptional("itemsPrefix", str, default="") == "001_"


def test_mandatory_key_fails_when_absent():
    node = MakeNode({"bundles": {"items": [{}]}}).SubOptional("bundles").Elements("items", dict)[0]
    with pytest.raises(AssertionError) as error:
        node.GetMandatory("name", str)
    assert str(error.value) == "ModBundleItems.json: bundles.items[0].name is required but is not set"


def test_bad_type_names_the_file_the_section_and_the_key():
    fileNode = MakeItemsNode().Elements("items", dict, nameKey="name")[3].Elements("files", dict)[2]
    with pytest.raises(AssertionError) as error:
        fileNode.GetOptional("target", str)
    assert str(error.value) == (
        "ModBundleItems.json: bundles.items[3] 'GameFiles'.files[2].target "
        "is type:int but should be type:str")


def test_element_type_is_verified_with_the_element_index():
    def MakePackNode(itemNames: list) -> util.JsonNode:
        data = {"bundles": {"packs": [{"name": "Core", "itemNames": itemNames}]}}
        return MakeNode(data).SubOptional("bundles").Elements("packs", dict, nameKey="name")[0]

    assert MakePackNode(["A", "B"]).GetMandatory("itemNames", list, elementType=str) == ["A", "B"]
    with pytest.raises(AssertionError) as error:
        MakePackNode(["A", 2]).GetMandatory("itemNames", list, elementType=str)
    assert str(error.value) == (
        "ModBundleItems.json: bundles.packs[0] 'Core'.itemNames[1] "
        "is type:int but should be type:str")


def test_verify_names_the_place_and_the_key():
    node = MakeNode({"folders": {"releaseDir": "Release"}}).SubOptional("folders")
    node.Verify(True, "must differ")
    with pytest.raises(AssertionError) as error:
        node.Verify(False, "must not equal buildDir", key="releaseDir")
    assert str(error.value) == "ModBundleItems.json: folders.releaseDir must not equal buildDir"


def test_union_and_tuple_expected_types_are_reported():
    node = MakeNode({"tools": {"version": []}}).SubOptional("tools")
    with pytest.raises(AssertionError) as error:
        node.GetOptional("version", (int, float))
    assert "but should be type:int or float" in str(error.value)


def test_an_absent_section_is_falsy_but_still_names_its_place():
    node = MakeNode({}).SubOptional("bundles")
    assert not node
    assert node.data == None
    assert node.Name("items") == "ModBundleItems.json: bundles.items"


def test_an_empty_section_is_falsy():
    # An empty section carries nothing to parse, so it is skipped like an absent one.
    assert not MakeNode({"bundles": {}}).SubOptional("bundles")


def test_a_section_of_the_wrong_type_is_reported_where_it_is_descended():
    with pytest.raises(AssertionError) as error:
        MakeNode({"bundles": []}).SubOptional("bundles")
    assert str(error.value) == "ModBundleItems.json: bundles is type:list but should be type:dict"


def test_an_absent_list_has_no_elements_at_all():
    assert MakeNode({"bundles": {}}).SubOptional("bundles").Elements("items", dict) == []


def test_elements_verify_the_element_type_with_the_element_index():
    node = MakeNode({"tools": {"list": [{}, "nope"]}}).SubOptional("tools")
    with pytest.raises(AssertionError) as error:
        node.Elements("list", dict)
    assert str(error.value) == "ModBundleItems.json: tools.list[1] is type:str but should be type:dict"


def test_a_list_that_is_not_a_list_is_reported_by_its_own_name():
    node = MakeNode({"tools": {"list": "nope"}}).SubOptional("tools")
    with pytest.raises(AssertionError) as error:
        node.Elements("list", dict)
    assert str(error.value) == "ModBundleItems.json: tools.list is type:str but should be type:list"


def test_elements_of_a_list_node_need_no_key_of_their_own():
    node = MakeNode({"build": {"files": ["a", "b"]}}).SubOptional("build")
    listNode = node.SubOptional("files", list, elementType=str)
    assert [element.data for element in listNode.Elements()] == ["a", "b"]
    assert listNode.Elements()[1].Name() == "ModBundleItems.json: build.files[1]"
