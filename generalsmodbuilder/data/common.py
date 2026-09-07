from typing import Any, Callable, Union
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


class ParamValueType:
    """
    The values that one known param accepts, and a description of them for a message.
    """
    description: str
    IsValid: Callable[[Any], bool]

    def __init__(self, description: str, isValid: Callable[[Any], bool]):
        self.description = description
        self.IsValid = isValid


def __IsString(value: Any) -> bool:
    return isinstance(value, str)


def __IsBool(value: Any) -> bool:
    return isinstance(value, bool)


def __IsCount(value: Any) -> bool:
    # bool is an int in python, but a switch is not a count and must be written as a number.
    return isinstance(value, int) and not isinstance(value, bool)


def __IsNumber(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def __IsNumberOrNumberPair(value: Any) -> bool:
    # One number applies to both dimensions of an image, two apply one per dimension.
    if isinstance(value, list):
        return len(value) in (1, 2) and all(__IsNumber(element) for element in value)
    return __IsNumber(value)


def __IsMarkerList(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    for marker in value:
        if not isinstance(marker, list) or len(marker) != 2:
            return False
        if not all(__IsString(token) and token for token in marker):
            return False
    return True


__TEXT_PARAM_TYPES: dict[str, ParamValueType] = {
    "forceEOL": ParamValueType("a string, for example a carriage return and a line feed", __IsString),
    "deleteComments": ParamValueType("a string, the token that begins a comment", __IsString),
    "deleteWhitespace": ParamValueType("a number, where any number above 0 deletes whitespace", __IsCount),
    "sourceEncoding": ParamValueType("a string, the name of a python codec", __IsString),
    "targetEncoding": ParamValueType("a string, the name of a python codec", __IsString),
    "excludeMarkersList": ParamValueType("a list of [begin, end] pairs of non empty strings", __IsMarkerList),
}

__GAME_TEXT_PARAM_TYPES: dict[str, ParamValueType] = {
    "language": ParamValueType("a string, the name of a game language", __IsString),
    "swapAndSetLanguage": ParamValueType("a string, the name of a game language", __IsString),
}

__IMAGE_PARAM_TYPES: dict[str, ParamValueType] = {
    "resize": ParamValueType("a number, or a list of one or two numbers", __IsNumberOrNumberPair),
    "rescale": ParamValueType("a number, or a list of one or two numbers", __IsNumberOrNumberPair),
    "resampling": ParamValueType("a string, the name of a resampling mode", __IsString),
}

__W3D_PARAM_TYPES: dict[str, ParamValueType] = {
    "w3dExportHierarchy": ParamValueType("true or false", __IsBool),
    "w3dExportAnimation": ParamValueType("true or false", __IsBool),
    "w3dExportMesh": ParamValueType("true or false", __IsBool),
    "w3dUseExistingSkeleton": ParamValueType("true or false", __IsBool),
    "w3dCompressTimeCoded": ParamValueType("true or false", __IsBool),
    "w3dForceVertexMaterials": ParamValueType("true or false", __IsBool),
    "w3dCreateIndividualFiles": ParamValueType("true or false", __IsBool),
    "w3dCreateTextureXmls": ParamValueType("true or false", __IsBool),
}

# The params that the build step reads, by their lower case name, because a bundle file may
# spell a param name in any case. The names above are lowered here, so that a table can
# spell a param the way it is meant to be read and a param cannot lose its verification by
# being declared in the wrong case. Every other param is an argument of a build tool and is
# passed on as it is written.
KNOWN_BUILD_FILE_PARAM_TYPES: dict[str, ParamValueType] = {
    name.lower(): paramType for name, paramType in {
        **__TEXT_PARAM_TYPES,
        **__GAME_TEXT_PARAM_TYPES,
        **__IMAGE_PARAM_TYPES,
        **__W3D_PARAM_TYPES,
    }.items()
}


def VerifyBuildFileParams(params: ParamsT, name: str) -> None:
    """
    Verifies the params of a bundle file. A param that the build step reads is verified
    against the values that it accepts, so that a wrong one is reported here instead of
    being ignored in silence while the build goes on to write a file that the param was
    meant to change. A param that the build step does not know is a build tool argument and
    is left alone, so that a tool can be given any argument it takes.
    """
    VerifyParamsType(params, name)

    for key, value in params.items():
        paramType: ParamValueType = KNOWN_BUILD_FILE_PARAM_TYPES.get(key.lower())
        if paramType != None and not paramType.IsValid(value):
            raise AssertionError(f'Object "{name}.{key}" is {value!r} but should be {paramType.description}')

