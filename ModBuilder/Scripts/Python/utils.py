import os.path
import winreg
import json
from os.path import join as joinpath
from os.path import normpath as normpath
from typing import Any


class JsonFile:
    path: str
    data: dict

    def __init__(self, path):
        self.path = normpath(path)
        self.data = self.__ReadJson(self.path)

    def __ReadJson(self, path: str) -> Any: # Raises exception on failure
        print("Read", path)
        file = open(path, "r")
        jsonText = file.read()
        jsonData = json.loads(jsonText)
        return jsonData

    def __PrintJson(self, path) -> None:
        print(json.dumps(path, indent=2, sort_keys=False))


def GetKeyValueFromRegistry(pathStr: str, keyStr: str) -> str:
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, pathStr, 0, winreg.KEY_READ)
        if key:
            value = winreg.QueryValueEx(key, keyStr)
            key.Close()
            if value and len(value) > 0:
                return value[0]
    except OSError:
        return None


def MakeFileDir(file: str) -> str:
    return os.path.dirname(os.path.realpath(file))


def GetSecondIfValid(first: Any, second: Any) -> Any:
    return second if second else first


def JoinPathIfValid(default: Any, *paths: str) -> Any:
    for path in paths:
        if not path or not isinstance(path, str):
            return default
    return joinpath(*paths)


def NormalizePath(path: str) -> str:
    return normpath(path)


def NormalizePaths(paths: list[str]) -> list[str]:
    for i in range(len(paths)):
        paths[i] = normpath(paths[i])
    return paths


def RelAssert(condition: bool, message: str = "") -> None:
    if not condition:
        raise Exception(message)
