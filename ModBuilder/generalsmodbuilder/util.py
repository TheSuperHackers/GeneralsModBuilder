import os
import sys
import types
import winreg
import json
import hashlib
import pickle
import shutil
import errno
from copy import copy
from typing import Any, Callable, Union


def Verify(condition: bool, message: str = "") -> None:
    if not condition:
        raise AssertionError(message)


def VerifyType(obj: object, expectedType: type | types.UnionType, objName: str) -> None:
    if not isinstance(obj, expectedType):
        raise AssertionError(f'Object "{objName}" is type:{type(obj).__name__} but should be type:{expectedType.__name__}')


def pprint(obj: Any) -> None:
    try:
        beeprintpp: function = None
        from beeprint import pp as beeprintpp
    except ImportError:
        pass
    if beeprintpp != None:
        beeprintpp(
            obj,
            max_depth=10,
            dict_ordered_key_enable=False,
            instance_repr_enable=False,
            list_in_line=False,
            tuple_in_line=False,
            string_break_enable=False)


def LoadPickle(path: str) -> Any:
    data: Any = None
    with open(path, "rb") as rfile:
        data = pickle.load(rfile)
    print("Loaded pickle", path)
    return data


def SavePickle(path: str, data: Any) -> None:
    MakeDirsForFile(path)
    with open(path, "wb") as wfile:
        pickle.dump(data, wfile, protocol=pickle.HIGHEST_PROTOCOL)
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
        VerifyType(self.path, str, "JsonFile.path")
        VerifyType(self.data, dict, "JsonFile.data")


def GetRegKeyValue(path, root=winreg.HKEY_LOCAL_MACHINE) -> Union[int, str, None]:
    path, name = str.split(path, sep=':')
    try:
        with winreg.OpenKey(root, path, 0, winreg.KEY_READ|winreg.KEY_WOW64_32KEY) as key:
            valuePair = winreg.QueryValueEx(key, name)
            if valuePair:
                print(f"Get registry key {path} : {name} as '{valuePair[0]}'")
                return valuePair[0]
            else:
                return None
    except OSError:
        return None


def SetRegKeyValue(path: str, value: Union[int, str], root=winreg.HKEY_LOCAL_MACHINE, regtype=None) -> bool:
    try:
        path, name = str.split(path, sep=':')
        with winreg.OpenKey(root, path, 0, winreg.KEY_WRITE|winreg.KEY_READ|winreg.KEY_WOW64_32KEY) as key:
            if regtype == None:
                regtype = winreg.QueryValueEx(key, name)[1]
            if regtype == None:
                if isinstance(value, int):
                    regtype = winreg.REG_DWORD
                else:
                    regtype = winreg.REG_SZ
            if regtype == winreg.REG_SZ:
                value = str(value)
            winreg.SetValueEx(key, name, 0, regtype, value)
            print(f"Set registry key {path} : {name} to '{value}'")
            return True
    except OSError:
        return False


def GetAbsFileDir(file: str) -> str:
    dir: str
    dir = os.path.dirname(file)
    dir = os.path.abspath(dir)
    return dir


g_isFrozen: bool = getattr(sys, 'frozen', False)

def GetAbsSmartFileDir(file: str) -> str:
    # If this code is frozen and the given file is part of it, then use the executable file dir.
    fileDir: str = GetAbsFileDir(file)
    if g_isFrozen:
        thisDir = os.path.dirname(__file__)
        if fileDir.startswith(thisDir):
            return os.path.dirname(sys.executable)
    return fileDir


def GetAbsFileDirs(file: str, absStopPath: str = "") -> list[str]:
    absStopPath = os.path.normpath(absStopPath)
    paths: list[str] = list()
    path1: str = GetAbsFileDir(file)
    path2: str = ""
    while path1 != absStopPath and path2 != path1:
        path2 = path1
        paths.append(path2)
        path1 = os.path.normpath(os.path.join(path2, ".."))
    return paths


def GetFileName(file: str) -> str:
    path, file = os.path.split(file)
    return file


def GetFileExt(file: str) -> str:
    path, ext = os.path.splitext(file)
    if ext and ext[0] == '.':
        ext = ext[1:]
    return ext


def GetFileDir(file: str) -> str:
    path, ext = os.path.split(file)
    return path


def GetFileDirAndName(file: str) -> str:
    path, ext = os.path.splitext(file)
    return path


def HasFileExt(file: str, expectedExt: str) -> bool:
    fileExt: str = GetFileExt(file)
    return fileExt.lower() == expectedExt.lower()


def HasAnyFileExt(file: str, expectedExtList: list[str]) -> bool:
    ext: str
    for ext in expectedExtList:
        if HasFileExt(file, ext):
            return True
    return False


def CreateRelPaths(paths: list[str], start: str) -> list[str]:
    relPaths = copy(paths)
    for i in range(len(relPaths)):
        relPaths[i] = os.path.relpath(path=relPaths[i], start=start)
    return relPaths


def MakeDirsForFile(file: str) -> None:
    os.makedirs(GetAbsFileDir(file), exist_ok=True)


def DeleteFile(path: str) -> bool:
    if os.path.islink(path):
        os.unlink(path)
        return True
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False


def DeleteFileOrPath(path: str) -> bool:
    if os.path.islink(path):
        os.unlink(path)
        return True
    if os.path.isfile(path):
        os.remove(path)
        return True
    if os.path.isdir(path):
        shutil.rmtree(path)
        return True
    return False


def JoinPathIfValid(default: Any, *paths: str) -> Any:
    for path in paths:
        if not path or not isinstance(path, str):
            return default
    return os.path.join(*paths)


def GetFileSize(path: str) -> str:
    return os.path.getsize(path)


def GetFileMd5(path: str) -> str:
    return GetFileHash(path, hashlib.md5)


def GetFileSha256(path: str) -> str:
    return GetFileHash(path, hashlib.sha256)


g_fileHashCount: int = 0

def GetFileHash(path: str, hashFunc: Callable) -> str:
    BUF_SIZE = 1024 * 64
    hashStr: str = ""
    if os.path.isfile(path):
        hashObj: hashlib._Hash = hashFunc()
        with open(path, "rb", buffering=BUF_SIZE) as rfile:
            for chunk in iter(lambda: rfile.read(BUF_SIZE), b""):
                hashObj.update(chunk)
        hashStr = hashObj.hexdigest()

        global g_fileHashCount
        g_fileHashCount += 1
        print(f"Hashed ({g_fileHashCount}) {path} as {hashStr}")
    return hashStr


def GetFileModifiedTime(path: str) -> float:
    if os.path.isfile(path):
        return os.path.getmtime(path)
    else:
        return 0.0


# Windows-specific error code indicating an invalid pathname.
# https://docs.microsoft.com/en-us/windows/win32/debug/system-error-codes--0-499-
ERROR_INVALID_NAME = 123

def IsValidPathName(pathname: str) -> bool:
    '''
    `True` if the passed pathname is a valid pathname for the current OS;
    `False` otherwise.
    '''
    if not isinstance(pathname, str) or not pathname:
        return False

    try:
        # Strip this pathname's Windows-specific drive specifier (e.g., `C:\`)
        # if any. Since Windows prohibits path components from containing `:`
        # characters, failing to strip this `:`-suffixed prefix would
        # erroneously invalidate all valid absolute Windows pathnames.
        _, pathname = os.path.splitdrive(pathname)

        # Directory guaranteed to exist. If the current OS is Windows, this is
        # the drive to which Windows was installed (e.g., the "%HOMEDRIVE%"
        # environment variable); else, the typical root directory.
        if sys.platform == 'win32':
            rootDir = os.environ.get('HOMEDRIVE', 'C:')
        else:
            rootDir = os.path.sep

        assert os.path.isdir(rootDir)

        # Append a path separator to this directory if needed.
        rootDir = rootDir.rstrip(os.path.sep) + os.path.sep

        # Test whether each path component split from this pathname is valid or
        # not, ignoring non-existent and non-readable path components.
        for pathnamePart in pathname.split(os.path.sep):
            try:
                os.lstat(rootDir + pathnamePart)
            # If an OS-specific exception is raised, its error code
            # indicates whether this pathname is valid or not. Unless this
            # is the case, this exception implies an ignorable kernel or
            # filesystem complaint (e.g., path not found or inaccessible).
            #
            # Only the following exceptions indicate invalid pathnames:
            #
            # * Instances of the Windows-specific "WindowsError" class
            #   defining the "winerror" attribute whose value is
            #   "ERROR_INVALID_NAME". Under Windows, "winerror" is more
            #   fine-grained and hence useful than the generic "errno"
            #   attribute. When a too-long pathname is passed, for example,
            #   "errno" is "ENOENT" (i.e., no such file or directory) rather
            #   than "ENAMETOOLONG" (i.e., file name too long).
            # * Instances of the cross-platform "OSError" class defining the
            #   generic "errno" attribute whose value is either:
            #   * Under most POSIX-compatible OSes, "ENAMETOOLONG".
            #   * Under some edge-case OSes (e.g., SunOS, *BSD), "ERANGE".
            except OSError as exc:
                if hasattr(exc, 'winerror'):
                    if exc.winerror == ERROR_INVALID_NAME:
                        return False
                elif exc.errno in {errno.ENAMETOOLONG, errno.ERANGE}:
                    return False
    # If a "TypeError" exception was raised, it almost certainly has the
    # error message "embedded NUL character" indicating an invalid pathname.
    except TypeError as exc:
        return False
    else:
        return True
