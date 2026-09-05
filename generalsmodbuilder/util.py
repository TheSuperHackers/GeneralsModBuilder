import os
import subprocess
import sys
import time
import types
try:
    import winreg
except ModuleNotFoundError:
    # winreg only exists on Windows. The registry functions below are no-ops
    # elsewhere, so that this module still imports on other platforms.
    winreg = None
import json
import hashlib
import pickle
import shutil
from copy import copy
from glob import glob
from typing import Any, Callable, Union, get_args


class Timer:
    start: float
    elapsed: float

    def __init__(self):
        self.start: float = time.time()
        self.elapsed: float = 0.0

    def Start(self) -> None:
        self.elapsed = 0.0
        self.start = time.time()

    def Finish(self) -> None:
        self.elapsed = time.time() - self.start

    def GetElapsedSeconds(self) -> float:
        if self.elapsed != 0.0:
            return self.elapsed
        else:
            return time.time() - self.start

    def GetElapsedSecondsString(self) -> str:
        elapsed = self.GetElapsedSeconds()
        return str.format("{:.3f}", elapsed)


PERFORMANCE_TIMER_THRESHOLD = 0.01


def Verify(condition: bool, message: str = "") -> None:
    if not condition:
        raise AssertionError(message)


def VerifyUniqueNames(names: list[str], nameDescription: str) -> None:
    """
    Fails when two names of the list name the same thing.
    Names are compared case insensitively, because file and directory names are case
    insensitive on Windows and in big archives, therefore two names that differ in
    upper and lower case only name the same file or directory.
    nameDescription : str
        Describes what the names are, for example "BundleItem 'Foo' target file".
    """
    keyToName = dict[str, str]()
    name: str

    for name in names:
        key: str = name.lower()
        firstName: str = keyToName.get(key)
        if firstName != None:
            if firstName == name:
                raise AssertionError(f"{nameDescription} '{name}' is used more than once")
            else:
                raise AssertionError(f"{nameDescription} '{name}' collides with '{firstName}', because "
                                     f"names that differ in upper and lower case only name the same thing")
        keyToName[key] = name


def GetTypeName(expectedType: type | tuple | types.UnionType) -> str:
    """
    Returns a readable name for anything that isinstance accepts as its second argument.
    Only a plain type carries __name__, so the name of a tuple of types and the name of
    a union of types have to be built from their members.
    """
    if isinstance(expectedType, tuple):
        names = [GetTypeName(member) for member in expectedType]
    else:
        members = get_args(expectedType)
        if not members:
            return getattr(expectedType, "__name__", str(expectedType))
        names = [GetTypeName(member) for member in members]

    if len(names) == 1:
        return names[0]
    return " or ".join([", ".join(names[:-1]), names[-1]])


def VerifyType(obj: object, expectedType: type | tuple | types.UnionType, objName: str) -> None:
    if not isinstance(obj, expectedType):
        raise AssertionError(f'Object "{objName}" is type:{type(obj).__name__} but should be type:{GetTypeName(expectedType)}')


def GetCheckedOptional(dictionary: dict, key: str, expectedTypeIfExists: type | tuple | types.UnionType) -> Any:
    value: Any = dictionary.get(key)
    if value != None:
        VerifyType(value, expectedTypeIfExists, key)
    return value


def GetCheckedMandatory(dictionary: dict, key: str, expectedType: type | tuple | types.UnionType) -> Any:
    value: Any = dictionary.get(key)
    VerifyType(value, expectedType, key)
    return value


def pprint(obj: Any) -> None:
    try:
        # Is imported here because it is not part of standard Python.
        from beeprint import pp as beeprintpp
        beeprintpp(
            obj,
            max_depth=10,
            dict_ordered_key_enable=False,
            instance_repr_enable=False,
            list_in_line=False,
            tuple_in_line=False,
            string_break_enable=False)
    except ImportError:
        pass


def LoadPickle(path: str) -> Any:
    print(f"Read pickle {path} ...")
    timer = Timer()
    data: Any = None
    with open(path, "rb") as rfile:
        data = pickle.load(rfile)
    if timer.GetElapsedSeconds() > PERFORMANCE_TIMER_THRESHOLD:
        print(f"Read pickle {path} completed in {timer.GetElapsedSecondsString()} s")
    return data


def SavePickle(path: str, data: Any) -> None:
    print(f"Write pickle {path} ...")
    timer = Timer()
    MakeDirsForFile(path)
    with open(path, "wb") as wfile:
        pickle.dump(data, wfile, protocol=pickle.HIGHEST_PROTOCOL)
    if timer.GetElapsedSeconds() > PERFORMANCE_TIMER_THRESHOLD:
        print(f"Write pickle {path} completed in {timer.GetElapsedSecondsString()} s")


def ReadJson(path: str) -> dict:
    print(f"Read json {path} ...")
    timer = Timer()
    data: dict = None
    with open(path, "rb") as rfile:
        text = rfile.read()
        data = json.loads(text)
    if timer.GetElapsedSeconds() > PERFORMANCE_TIMER_THRESHOLD:
        print(f"Read json {path} completed in {timer.GetElapsedSecondsString()} s")
    return data


def ReadYaml(path: str) -> dict:
    # Is imported here because it is not part of standard Python.
    from yaml import safe_load
    print(f"Read yaml {path} ...")
    timer = Timer()
    data: dict = None
    with open(path, "rb") as rfile:
        text = rfile.read()
        data = safe_load(text)
    if timer.GetElapsedSeconds() > PERFORMANCE_TIMER_THRESHOLD:
        print(f"Read yaml {path} completed in {timer.GetElapsedSecondsString()} s")
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


class YamlFile:
    path: str
    data: dict

    def __init__(self, path: str):
        self.path = os.path.normpath(path)
        self.data = ReadYaml(path)
        self.VerifyTypes()

    def VerifyTypes(self) -> None:
        VerifyType(self.path, str, "YamlFile.path")
        VerifyType(self.data, dict, "YamlFile.data")


class JsonContext:
    """
    Names the place inside a json file that a value is read from, so that a failure
    points at the file, the section and the key that the user wrote, instead of at the
    python field that the value ends up in.

    A context is built up while descending into the data, for example

        ctx = JsonContext(jsonFile.path).Sub("bundles").Sub("items").At(3, "GameFiles")
        ctx.Sub("files").At(2).GetOptional(jFile, "target", str)

    which reports a bad value as

        ModBundleItems.json: bundles.items[3] 'GameFiles'.files[2].target
        is type:int but should be type:str
    """
    absPath: str
    path: str

    def __init__(self, absPath: str, path: str = ""):
        self.absPath = absPath
        self.path = path

    def Sub(self, key: str) -> "JsonContext":
        """
        Names a nested object or list, for example 'items' below 'bundles'.
        """
        return JsonContext(self.absPath, self.__Join(key))

    def At(self, index: int, name: str = "") -> "JsonContext":
        """
        Names one element of a list. The optional name identifies the element the way
        the user knows it, which is far more useful than its index alone.
        """
        path: str = f"{self.path}[{index}]"
        if name:
            path += f" '{name}'"
        return JsonContext(self.absPath, path)

    def Name(self, key: str = "") -> str:
        """
        The full name of this place, or of a key at this place, as it appears in a message.
        """
        return f"{self.absPath}: {self.__Join(key)}" if key else f"{self.absPath}: {self.path}"

    def Verify(self, condition: bool, message: str, key: str = "") -> None:
        """
        Fails with a message that names this place, or a key at this place.
        """
        Verify(condition, f"{self.Name(key)} {message}")

    def VerifyKnownKeys(self, jDict: dict, knownKeys: set) -> None:
        """
        Fails on a key that the format does not define. Such a key is otherwise ignored
        in silence, so a misspelled one behaves as if it had never been written at all.
        """
        for key in jDict:
            if key not in knownKeys:
                raise AssertionError(f"{self.Name(key)} is not a known key. "
                                     f"Known keys here are {', '.join(sorted(knownKeys))}")

    def GetOptional(
            self,
            jDict: dict,
            key: str,
            expectedType: type | tuple | types.UnionType,
            default: Any = None,
            elementType: type | tuple | types.UnionType = None) -> Any:
        """
        Reads a key that the format allows to be absent, and returns default when it is.
        """
        value: Any = jDict.get(key)
        if value == None:
            return default
        self.__VerifyValue(value, expectedType, key, elementType)
        return value

    def GetMandatory(
            self,
            jDict: dict,
            key: str,
            expectedType: type | tuple | types.UnionType,
            elementType: type | tuple | types.UnionType = None) -> Any:
        """
        Reads a key that the format requires, and fails when it is absent.
        """
        value: Any = jDict.get(key)
        if value == None:
            raise AssertionError(f"{self.Name(key)} is required but is not set")
        self.__VerifyValue(value, expectedType, key, elementType)
        return value

    def __Join(self, key: str) -> str:
        if not key:
            return self.path
        return f"{self.path}.{key}" if self.path else key

    def __VerifyValue(
            self,
            value: Any,
            expectedType: type | tuple | types.UnionType,
            key: str,
            elementType: type | tuple | types.UnionType) -> None:
        if not isinstance(value, expectedType):
            raise AssertionError(f"{self.Name(key)} is type:{type(value).__name__} "
                                 f"but should be type:{GetTypeName(expectedType)}")
        if elementType != None:
            for index, element in enumerate(value):
                if not isinstance(element, elementType):
                    raise AssertionError(f"{self.Name(key)}[{index}] is type:{type(element).__name__} "
                                         f"but should be type:{GetTypeName(elementType)}")


def GetRegKeyValue(path, root=None) -> Union[int, str, None]:
    if winreg == None:
        return None
    if root == None:
        root = winreg.HKEY_LOCAL_MACHINE
    path, name = str.split(path, sep=':')
    try:
        with winreg.OpenKey(root, path, 0, winreg.KEY_READ|winreg.KEY_WOW64_32KEY) as key:
            valuePair = winreg.QueryValueEx(key, name)
            if valuePair:
                print(f"Get registry key {path} : {name} as '{valuePair[0]}'")
                return valuePair[0]
            return None
    except OSError:
        return None


def SetRegKeyValue(path: str, value: Union[int, str], root=None, regtype=None) -> bool:
    if winreg == None:
        return False
    if root == None:
        root = winreg.HKEY_LOCAL_MACHINE
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


def GetSubdirsAndFilesRecursively(dir: str) -> tuple[list, list]:
    subdirs, files = [], []

    if os.path.isdir(dir):
        for f in os.scandir(dir):
            if f.is_dir():
                subdirs.append(f.path)
            elif f.is_file() or f.is_symlink():
                files.append(f.path)

    for subdir in list(subdirs):
        rsubdirs, rfiles = GetSubdirsAndFilesRecursively(subdir)
        subdirs.extend(rsubdirs)
        files.extend(rfiles)

    return subdirs, files


def GetAbsFileDir(file: str) -> str:
    fdir: str
    fdir = os.path.dirname(file)
    fdir = os.path.abspath(fdir)
    return fdir


# The directory of the installed generalsmodbuilder package. Data files that ship
# with the package, such as the built-in configurations and the gui icon, live here.
g_appDir: str = GetAbsFileDir(__file__)


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


def GetFileName(filepath: str) -> str:
    path, file = os.path.split(filepath)
    return file


def GetFileNameNoExt(filepath: str) -> str:
    path, file = os.path.split(filepath)
    name, ext = os.path.splitext(file)
    return name


def GetFileExt(filepath: str) -> str:
    path, ext = os.path.splitext(filepath)
    if ext and ext[0] == '.':
        ext = ext[1:]
    return ext


def GetFileDir(filepath: str) -> str:
    path, file = os.path.split(filepath)
    return path


def GetFileDirAndName(filepath: str) -> str:
    path, ext = os.path.splitext(filepath)
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


def ResolveFileWildcards(fileList: list[str], sortWildcardMatches: bool = False, filesMustExist: bool = True) -> list[str]:
    """
    Substitutes every file path that contains a wildcard with all files that it matches.
    File paths without wildcard are taken over as is.
    filesMustExist : bool
        Fails when a path without wildcard names no file, and reports a wildcard that
        matches nothing. Pass False for a list that describes which files are allowed to
        be present rather than which files are required, such as the regular game data
        files, where the entries of every language that is not installed match nothing.
    sortWildcardMatches : bool
        Sorts the matches of each wildcard alphabetically. This makes the resulting order
        reproducible across machines, because glob returns matches in file system order.
        Files that are listed without wildcard always keep their listed order.
    """
    newFiles = list[str]()
    file: str
    for file in fileList:
        if "*" in file and not os.path.isfile(file):
            globFiles: list[str] = glob(file, recursive=True)
            if filesMustExist and not bool(globFiles):
                print(f"Note: Wildcard '{file}' currently matches nothing")

            globFiles = [globFile for globFile in globFiles if os.path.isfile(globFile)]
            if sortWildcardMatches:
                globFiles.sort()

            newFiles.extend(globFiles)
        else:
            if filesMustExist:
                Verify(os.path.isfile(file), f"File '{file}' is not a valid file")
            newFiles.append(file)
    return newFiles


def CreateRelPaths(paths: list[str], start: str) -> list[str]:
    relPaths = copy(paths)
    for i in range(len(relPaths)):
        relPaths[i] = os.path.relpath(path=relPaths[i], start=start)
    return relPaths


def MakeDirsForFile(file: str) -> None:
    os.makedirs(GetAbsFileDir(file), exist_ok=True)


# This implementation is
# - about 25% faster than testing os.path.islink, os.path.isfile before unlink or remove.
# - about 10% faster than unlink with a new pathlib.Path instance.
def DeleteFile(path: str) -> bool:
    """
    Delete file or symlink.
    """
    try:
        os.unlink(path)
        return True
    except OSError:
        pass
    try:
        os.remove(path)
        return True
    except OSError:
        pass
    return False


def DeleteFileOrDir(path: str) -> bool:
    """
    Delete file, symlink or directory tree.
    """
    try:
        os.unlink(path)
        return True
    except OSError:
        pass
    try:
        os.remove(path)
        return True
    except OSError:
        pass
    try:
        shutil.rmtree(path)
        return True
    except OSError:
        pass
    return False


def DeleteDir(path: str) -> bool:
    """
    Delete directory tree.
    """
    try:
        shutil.rmtree(path)
        return True
    except OSError:
        pass
    return False


def DeleteEmptyDir(path: str) -> bool:
    """
    Delete directory tree.
    """
    try:
        os.rmdir(path)
        return True
    except OSError:
        pass
    return False


def JoinPathIfValid(default: Any, *paths: str) -> Any:
    for path in paths:
        if not path or not isinstance(path, str):
            return default
    return os.path.join(*paths)


def GetFileSize(path: str) -> str:
    return os.path.getsize(path)


def GetFileMd5(path: str, log: bool=True) -> str:
    return GetFileHash(path, hashlib.md5, log)


def GetFileSha256(path: str, log: bool=True) -> str:
    return GetFileHash(path, hashlib.sha256, log)


g_fileHashCount: int = 0

def ResetFileHashCount() -> None:
    global g_fileHashCount
    g_fileHashCount = 0


def GetFileHash(path: str, hashFunc: Callable, log: bool=True) -> str:
    BUF_SIZE = 1024 * 64
    hashStr: str = ""
    try:
        timer = Timer()
        with open(path, "rb", buffering=BUF_SIZE) as rfile:
            hashObj: hashlib._Hash = hashFunc()
            for chunk in iter(lambda: rfile.read(BUF_SIZE), b""):
                hashObj.update(chunk)
            hashStr = hashObj.hexdigest()

            global g_fileHashCount
            g_fileHashCount += 1
            if log:
                print(f"Hashed ({g_fileHashCount}) {path} as {hashStr} in {timer.GetElapsedSecondsString()} s")
    except:
        pass
    return hashStr


def GetFileModifiedTime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


if sys.platform == 'win32':
    g_disallowedPathChars = set("<>\"|?*/")
else:
    g_disallowedPathChars = set()

def IsValidPathName(pathname: str) -> bool:
    s = set(pathname)
    for c in g_disallowedPathChars:
        if c in s:
            return False
    return True


def RunProcess(args) -> bool:
    subprocess.run(args=args, check=True)
    return True
