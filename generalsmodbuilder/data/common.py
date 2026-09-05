from typing import Union
from generalsmodbuilder import util


ParamT = Union[str, int, float, bool, list]
ParamsT = dict[str, Union[str, int, float, bool, list[ParamT]]]


class ParsedData:
    """
    The phases that a data object parsed from json goes through. Every parser builds its
    objects from the json first and then runs these, so that each phase can rely on the
    ones before it. Subclasses implement the phases that apply to them.

    Types are not verified here that are already verified where the json value is read.
    What VerifyTypes is still for is state that a read cannot see: values computed after
    parsing, and the result of merging several json files, where a key may be set by any
    one of them.
    """

    def VerifyTypes(self) -> None:
        pass

    def Normalize(self) -> None:
        pass

    def ResolveWildcards(self) -> None:
        pass

    def VerifyValues(self) -> None:
        pass


def FinalizeParsedData(data: ParsedData) -> None:
    """
    Runs the phases in the one order that they are valid in. Types are verified first so
    that the later phases can rely on them, paths are normalized next, wildcards are
    resolved against normalized paths, and the values are verified last, when they are
    the values that will actually be used.
    """
    data.VerifyTypes()
    data.Normalize()
    data.ResolveWildcards()
    data.VerifyValues()


def VerifyParamsType(params: ParamsT, name: str) -> None:
    for key,value in params.items():
        util.VerifyType(key, str, f"{name}.key")
        util.VerifyType(value, (str, int, float, bool, list), f"{name}.value")

        if isinstance(value, list):
            for subValue in value:
                util.VerifyType(subValue, (str, int, float, bool, list), f"{name}.value.value")


def VerifyStringListType(strlist: list[str], name: str) -> None:
    util.VerifyType(strlist, list, name)
    for value in strlist:
        util.VerifyType(value, str, f"{name}.value")
