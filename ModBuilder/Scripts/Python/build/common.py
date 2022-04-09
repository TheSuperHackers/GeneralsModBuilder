from data.common import ParamT, ParamsT


def ParamsToArgs(params: ParamsT) -> list[str]:
    args = list()
    for key,value in params.items():
        __AppendParamToArgs(args, key)

        if isinstance(value, list):
            for subValue in value:
                __AppendParamToArgs(args, subValue)
        else:
            __AppendParamToArgs(args, value)

    return args


def __AppendParamToArgs(args: list[str], val: ParamT) -> None:
    if strVal := str(val):
        args.append(strVal)
