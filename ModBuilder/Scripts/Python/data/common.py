import utils
from typing import Union


ParamT = Union[str, int, float, bool]
ParamsT = dict[str, Union[str, int, float, bool, list[ParamT]]]


def VerifyParamsType(params: ParamsT, name: str) -> None:
    for key,value in params.items():
        utils.RelAssert(isinstance(key, str), f"{name} has incorrect type")
        utils.RelAssert(isinstance(value, str) or
            isinstance(value, int) or
            isinstance(value, float) or
            isinstance(value, bool) or
            isinstance(value, list), f"{name} has incorrect type")

        if isinstance(value, list):
            for subValue in value:
                utils.RelAssert(
                    isinstance(subValue, str) or
                    isinstance(subValue, int) or
                    isinstance(subValue, float) or
                    isinstance(subValue, bool), f"{name} has incorrect type")


def VerifyStringListType(strlist: list[str], name: str) -> None:
    utils.RelAssert(isinstance(strlist, list), f"{name} has incorrect type")
    for e in strlist:
        utils.RelAssert(isinstance(e, str), f"{name} has incorrect type")
