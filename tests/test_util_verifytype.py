import types
from typing import Optional, Union

import pytest

from generalsmodbuilder import util


def test_plain_type_is_named():
    assert util.GetTypeName(str) == "str"


def test_tuple_of_types_is_named():
    assert util.GetTypeName((str, int)) == "str or int"
    assert util.GetTypeName((str, int, float, bool, list)) == "str, int, float, bool or list"


def test_union_types_are_named():
    assert util.GetTypeName(Union[int, None]) == "int or NoneType"
    assert util.GetTypeName(Optional[int]) == "int or NoneType"
    assert util.GetTypeName(int | None) == "int or NoneType"
    assert util.GetTypeName(str | types.NoneType) == "str or NoneType"


def test_verify_type_accepts_matching_values():
    util.VerifyType("a", str, "Thing.name")
    util.VerifyType(1, (str, int), "Thing.value")
    util.VerifyType(None, Union[int, None], "Thing.optional")
    util.VerifyType(1, int | None, "Thing.optional")


# A failing check used to raise AttributeError while building its own message,
# because only a plain type carries __name__.
@pytest.mark.parametrize("expectedType", [
    str,
    (str, int, float, bool, list),
    Union[int, None],
    int | None,
])
def test_verify_type_reports_a_mismatch_as_assertion_error(expectedType):
    with pytest.raises(AssertionError) as error:
        util.VerifyType(object(), expectedType, "Thing.value")
    assert "Thing.value" in str(error.value)
    assert "is type:object" in str(error.value)
