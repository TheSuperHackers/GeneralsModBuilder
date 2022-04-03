import os
import winreg
import json
import hashlib
import pickle
from typing import Any
from beeprint import pp


def pprint(obj: Any) -> None:
    pp(
        obj,
        max_depth=10,
        dict_ordered_key_enable=False,
        instance_repr_enable=False,
        list_in_line=False,
        tuple_in_line=False)


def SerializeLoad(path: str) -> Any:
    print("Serialize Load", path)
    data: Any = None
    with open(path, "rb") as rfile:
        data = pickle.load(rfile)
    return data


def SerializeSave(path: str, data: Any) -> None:
    print("Serialize Save", path)
    MakeDirsForFile(path)
    with open(path, "wb") as wfile:
	    pickle.dump(data, wfile)


def ReadJson(path: str) -> dict:
    print("Read Json", path)
    data: dict = None
    with open(path, "rb") as rfile:
        text = rfile.read()
        data = json.loads(text)
    return data


class JsonFile:
    path: str
    data: dict

    def __init__(self, path: str):
        self.path = os.path.normpath(path)
        self.data = ReadJson(path)
        self.VerifyTypes()

    def VerifyTypes(self) -> None:
        RelAssert(isinstance(self.path, str), "JsonFile.path has incorrect type")
        RelAssert(isinstance(self.data, dict), "JsonFile.data has incorrect type")


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


def GetFileExt(file: str) -> str:
    path, ext = os.path.splitext(file)
    return ext


def HasFileExt(file: str, ext: str) -> str:
    return file.lower().endswith(ext.lower())


def MakeDirsForFile(file: str) -> None:
    os.makedirs(GetFileDir(file), exist_ok=True)


def GetSecondIfValid(first: Any, second: Any) -> Any:
    return second if second else first


def JoinPathIfValid(default: Any, *paths: str) -> Any:
    for path in paths:
        if not path or not isinstance(path, str):
            return default
    return os.path.join(*paths)


def NormalizePath(path: str) -> str:
    return os.path.normpath(path)


def NormalizePaths(paths: list[str]) -> list[str]:
    for i in range(len(paths)):
        paths[i] = os.path.normpath(paths[i])
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


def IsPathSyntax(s: str) -> bool:
    if s and isinstance(s, str) and (s.endswith("/") or s.endswith("\\")):
        return True
    return False
