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


def VerifyFormatVersion(node: util.JsonNode, latestVersion: int) -> int:
    """
    Reads the format version of a section. The version exists so that the parsers can
    adapt to older and newer data once a breaking change is made to the json format, so
    a version that this build does not know is rejected here rather than parsed as if it
    were the current one. A section without a version is assumed to be the current one.
    """
    version: int = node.GetOptional("version", int, latestVersion)
    node.Verify(version >= 1, f"is {version}, but a format version starts at 1", key="version")
    node.Verify(version <= latestVersion,
               f"is {version}, but this build knows the format only up to version {latestVersion}",
               key="version")
    return version


def VerifyParamsType(params: ParamsT, name: str) -> None:
    for key,value in params.items():
        util.VerifyType(key, str, f"{name}.key")
        util.VerifyType(value, (str, int, float, bool, list), f"{name}.value")

        if isinstance(value, list):
            for subValue in value:
                util.VerifyType(subValue, (str, int, float, bool, list), f"{name}.value.value")

