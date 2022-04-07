import os
import winreg
import json
import hashlib
import pickle
import shutil
from copy import copy
from typing import Any, Callable
from beeprint import pp


def pprint(obj: Any) -> None:
    pp(
        obj,
        max_depth=10,
        dict_ordered_key_enable=False,
        instance_repr_enable=False,
        list_in_line=False,
        tuple_in_line=False)


def LoadPickle(path: str) -> Any:
    data: Any = None
    with open(path, "rb") as rfile:
        data = pickle.load(rfile)
    print("Loaded pickle", path)
    return data


def SavePickle(path: str, data: Any) -> None:
    MakeDirsForFile(path)
    with open(path, "wb") as wfile:
        pickle.dump(data, wfile)
    print("Saved pickle", path)


def ReadJson(path: str) -> dict:
    print("Read json", path)
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
    return os.path.dirname(file)


def GetAllFileDirs(file: str, stopPath: str = "") -> list[str]:
    paths: list[str] = list()
    path1: str = os.path.dirname(file)
    path2: str = ""
    while path1 != stopPath and path2 != path1:
        path2 = path1
        paths.append(path2)
        path1 = os.path.normpath(os.path.join(path2, ".."))
    return paths


def GetFileName(file: str) -> str:
    path, file = os.path.split(file)
    return file


def GetFileExt(file: str) -> str:
    path, ext = os.path.splitext(file)
    return ext


def GetFileDirAndName(file: str) -> str:
    path, ext = os.path.splitext(file)
    return path


def HasFileExt(file: str, ext: str) -> str:
    return file.lower().endswith(ext.lower())


def CreateRelPaths(paths: list[str], start: str) -> list[str]:
    relPaths = copy(paths)
    for i in range(len(relPaths)):
        relPaths[i] = os.path.relpath(path=relPaths[i], start=start)
    return relPaths


def MakeDirsForFile(file: str) -> None:
    os.makedirs(GetFileDir(file), exist_ok=True)


def DeleteFileOrPath(path: str) -> bool:
    if os.path.isfile(path):
        os.remove(path)
        return True
    elif os.path.isdir(path):
        shutil.rmtree(path)
        return True
    else:
        return False


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


def GetFileMd5(path: str) -> str:
    return GetFileHash(path, hashlib.md5)


def GetFileSha256(path: str) -> str:
    return GetFileHash(path, hashlib.sha256)


def GetFileHash(path, hashFunc: Callable) -> str:
    hashStr: str = ""
    if os.path.isfile(path):
        hashObj: hashlib._Hash = hashFunc()
        with open(path, "rb") as rfile:
            for chunk in iter(lambda: rfile.read(4096), b""):
                hashObj.update(chunk)
        hashStr = hashObj.hexdigest()
        print(f"Hashed {path} as {hashStr}")
    return hashStr


def IsPathSyntax(path: str) -> bool:
    if path and isinstance(path, str) and (path.endswith("/") or path.endswith("\\")):
        return True
    return False
