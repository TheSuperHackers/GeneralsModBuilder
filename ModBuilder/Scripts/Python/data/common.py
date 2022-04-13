import utils
from typing import Union


ParamT = Union[str, int, float, bool]
ParamsT = dict[str, Union[str, int, float, bool, list[ParamT]]]


def VerifyParamsType(params: ParamsT, name: str) -> None:
    for key,value in params.items():
        utils.RelAssertType(key, str, f"{name}.key")
        utils.RelAssertType(value, (str, int, float, bool, list), f"{name}.value")

        if isinstance(value, list):
            for subValue in value:
                utils.RelAssertType(subValue, (str, int, float, bool), f"{name}.value.value")


def VerifyStringListType(strlist: list[str], name: str) -> None:
    utils.RelAssertType(strlist, list, name)
    for value in strlist:
        utils.RelAssertType(value, str, f"{name}.value")
