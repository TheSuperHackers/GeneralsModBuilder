import os
from typing import Union
from generalsmodbuilder import util


ParamT = Union[str, int, float, bool]
ParamsT = dict[str, Union[str, int, float, bool, list[ParamT]]]


def __MakeAbsolutePathIfApplicable(path: str, absDir: str) -> str | None:
    newpath = path.removeprefix("{MAKE_ABSOLUTE}")
    if newpath != path:
        newpath = newpath.removeprefix("/")
        newpath = newpath.removeprefix("\\")
        newpath = os.path.join(absDir, newpath)
        newpath = os.path.normpath(newpath)
        return newpath
    return None


def ProcessParams(params: ParamsT, absDir: str = "") -> ParamsT:
    newparams = params.copy()

    for key,value in newparams.items():
        if isinstance(value, str):
            newValue = __MakeAbsolutePathIfApplicable(value, absDir)
            if newValue:
                newparams[key] = newValue
            continue

        if isinstance(value, list):
            for index, subValue in enumerate(value):
                if isinstance(subValue, str):
                    newValue = __MakeAbsolutePathIfApplicable(subValue, absDir)
                    if newValue:
                        newparams[key][index] = newValue
            continue

    return newparams


def VerifyParamsType(params: ParamsT, name: str) -> None:
    for key,value in params.items():
        util.VerifyType(key, str, f"{name}.key")
        util.VerifyType(value, (str, int, float, bool, list), f"{name}.value")

        if isinstance(value, list):
            for subValue in value:
                util.VerifyType(subValue, (str, int, float, bool), f"{name}.value.value")


def VerifyStringListType(strlist: list[str], name: str) -> None:
    util.VerifyType(strlist, list, name)
    for value in strlist:
        util.VerifyType(value, str, f"{name}.value")
