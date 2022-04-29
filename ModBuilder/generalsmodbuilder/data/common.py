from typing import Union
from generalsmodbuilder import util


ParamT = Union[str, int, float, bool]
ParamsT = dict[str, Union[str, int, float, bool, list[ParamT]]]


def VerifyParamsType(params: ParamsT, name: str) -> None:
    for key,value in params.items():
        util.RelAssertType(key, str, f"{name}.key")
        util.RelAssertType(value, (str, int, float, bool, list), f"{name}.value")

        if isinstance(value, list):
            for subValue in value:
                util.RelAssertType(subValue, (str, int, float, bool), f"{name}.value.value")


def VerifyStringListType(strlist: list[str], name: str) -> None:
    util.RelAssertType(strlist, list, name)
    for value in strlist:
        util.RelAssertType(value, str, f"{name}.value")
