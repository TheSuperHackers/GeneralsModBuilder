import os
import winreg
import json
import hashlib
from os.path import join as joinpath
from os.path import normpath as normpath
from typing import Any


class JsonFile:
    path: str
    data: dict

    def __init__(self, path: str):
        self.path = normpath(path)
        self.data = self.__ReadJson(self.path)
        RelAssert(isinstance(self.path, str), "JsonFile.path has incorrect type")
        RelAssert(isinstance(self.data, dict), "JsonFile.data has incorrect type")

    def __ReadJson(self, path: str) -> dict:
        print("Read Json", path)
        jsonData = dict()
        with open(path, "rb") as rfile:
            jsonText = rfile.read()
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


def GetFileDir(file: str) -> str:
    return os.path.dirname(os.path.realpath(file))


def MakeDirsForFile(file: str) -> None:
    os.makedirs(GetFileDir(file), exist_ok=True)


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


def GetFileMd5(path) -> str:
    print("Get md5", path)
    md5 = hashlib.md5()
    with open(path, "rb") as rfile:
        for chunk in iter(lambda: rfile.read(4096), b""):
            md5.update(chunk)
    return md5.hexdigest()
