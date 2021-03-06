import importlib
import shutil
import subprocess
import json
import os
import platform
import sys
import hashlib
from timeit import default_timer as timer
from typing import Callable, Union


def GetAbsFileDir(file: str) -> str:
    dir: str
    dir = os.path.dirname(file)
    dir = os.path.abspath(dir)
    return dir


def GetFileDirAndName(file: str) -> str:
    path, ext = os.path.splitext(file)
    return path


def GetFileName(file: str) -> str:
    path, name = os.path.split(file)
    return name


def GetFileSize(path: str) -> str:
    return os.path.getsize(path)


def GetFileMd5(path: str) -> str:
    return GetFileHash(path, hashlib.md5)


def GetFileSha256(path: str) -> str:
    return GetFileHash(path, hashlib.sha256)


def GetFileHash(path: str, hashFunc: Callable) -> str:
    hashStr: str = ""
    if os.path.isfile(path):
        hashObj: hashlib._Hash = hashFunc()
        with open(path, "rb") as rfile:
            for chunk in iter(lambda: rfile.read(4096), b""):
                hashObj.update(chunk)
        hashStr = hashObj.hexdigest()
    return hashStr


g_writeFileCount: int = 0

def WriteFile(path: str, data: bytes) -> None:
    if len(data) > 0:
        with open(path, 'wb') as f:
            written: int = f.write(data)
            assert(written == len(data))
        global g_writeFileCount
        g_writeFileCount += 1
        print(f"Created file ({g_writeFileCount}) '{path}'")


def DeleteFileOrPath(path: str) -> bool:
    if os.path.islink(path):
        os.unlink(path)
        return True
    if os.path.isfile(path):
        os.remove(path)
        return True
    elif os.path.isdir(path):
        shutil.rmtree(path)
        return True
    else:
        return False


def __GenerateHashFiles(file: str) -> None:
    if os.path.isfile(file):
        hashDir: str = os.path.join(GetAbsFileDir(file), "hashes")
        hashFile: str = os.path.join(hashDir, GetFileName(file))
        os.makedirs(hashDir, exist_ok=True)

        md5: str = GetFileMd5(file)
        sha256: str = GetFileSha256(file)
        size: str = GetFileSize(file)

        WriteFile(hashFile + ".md5", str.encode(md5))
        WriteFile(hashFile + ".sha256", str.encode(sha256))
        WriteFile(hashFile + ".size", str.encode(str(size)))


def GenerateHashFiles(files: Union[str, list[str]]) -> None:
    if isinstance(files, str):
        __GenerateHashFiles(files)
    elif isinstance(files, list):
        for file in files:
            __GenerateHashFiles(file)


def RelAssert(condition: bool, message: str = "") -> None:
    if not condition:
        raise Exception(message)


def RelAssertType(obj: object, expectedType: type, objName: str) -> None:
    if not isinstance(obj, expectedType):
        raise Exception(f'Object "{objName}" is type:{type(obj).__name__} but should be type:{expectedType.__name__}')


def JoinPathIfValid(default, *paths: str) -> str:
    for path in paths:
        if not path or not isinstance(path, str):
            return default
    return os.path.join(*paths)


def ChangeDir(dir: str) -> None:
    print(f"chdir '{dir}'")
    os.chdir(dir)


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
        RelAssertType(self.path, str, "JsonFile.path")
        RelAssertType(self.data, dict, "JsonFile.data")


class PyPackage:
    absWhl: str

    def __init__(self):
        pass

    def AbsDir(self) -> str:
        return os.path.dirname(self.absWhl)

    def AbsWhl(self) -> str:
        return self.absWhl

    def VerifyTypes(self) -> None:
        if self.absWhl != None:
            RelAssertType(self.absWhl, str, "PyPackage.absWhl")

    def VerifyValues(self) -> None:
        if self.absWhl != None:
            RelAssert(os.path.isfile(self.AbsWhl()), f"PyPackage.absWhl '{self.AbsWhl()}' is not a valid file")

    def Normalize(self) -> None:
        if self.absWhl != None:
            self.absWhl = os.path.normpath(self.absWhl)


class BuildSetup:
    absVenvDir: str
    absVenvExe: str
    absPythonExe: str
    packages: list[PyPackage]
    pipInstalls: list[str]

    def __init__(self):
        self.packages = list[PyPackage]()

    def VerifyTypes(self) -> None:
        RelAssertType(self.absVenvDir, str, "BuildSetup.absVenvDir")
        RelAssertType(self.absVenvExe, str, "BuildSetup.absVenvExe")
        RelAssertType(self.absPythonExe, str, "BuildSetup.absPythonExe")
        RelAssertType(self.packages, list, "BuildSetup.packages")
        RelAssertType(self.pipInstalls, list, "BuildSetup.pipInstalls")
        for package in self.packages:
            RelAssertType(package, PyPackage, "BuildSetup.packages")
            package.VerifyTypes()
        for name in self.pipInstalls:
            RelAssertType(name, str, "BuildSetup.pipInstalls")

    def VerifyValues(self) -> None:
        RelAssert(os.path.isfile(self.absPythonExe), f"BuildSetup.absPythonExe '{self.absPythonExe}' is not a valid file" )
        for package in self.packages:
            package.VerifyValues()

    def Normalize(self) -> None:
        self.absVenvDir = os.path.normpath(self.absVenvDir)
        self.absVenvExe = os.path.normpath(self.absVenvExe)
        self.absPythonExe = os.path.normpath(self.absPythonExe)
        for package in self.packages:
            package.Normalize()


class BuildStep:
    absDir: str
    name: str
    setup: BuildSetup
    config: dict

    def __init__(self):
        self.config = dict()

    def MakeAbsPath(self, relPath: str) -> str:
        RelAssertType(relPath, str, "relPath")
        path: str = os.path.join(self.absDir, relPath)
        path = os.path.normpath(path)
        return path

    def VerifyTypes(self) -> None:
        RelAssertType(self.absDir, str, "BuildStep.absDir")
        RelAssertType(self.name, str, "BuildStep.name")
        RelAssertType(self.setup, BuildSetup, "BuildSetup.absVenvExe")
        RelAssertType(self.config, dict, "BuildSetup.absPythonExe")
        self.setup.VerifyTypes()

    def VerifyValues(self) -> None:
        RelAssert(os.path.isdir(self.absDir), f"BuildStep.absDir '{self.absDir}' is not an valid path")
        RelAssert(self.name, "BuildStep.name must not be empty")
        self.setup.VerifyValues()

    def Normalize(self) -> None:
        self.setup.Normalize()


BuildStepsT = list[BuildStep]


def __MakeBuildJsonPath() -> str:
    return os.path.join(GetAbsFileDir(__file__), "build.json")


def __MakeBuildSetupFromDict(jSetup: dict, absDir: str) -> BuildSetup:
    buildSetup = BuildSetup()
    buildSetup.pipInstalls = jSetup.get("pipInstalls")
    platfrm: str = sys.platform.lower()
    machine: str = platform.machine().lower()
    jPlatform: dict = jSetup.get(platfrm)

    if jPlatform:
        buildSetup.absVenvDir = JoinPathIfValid(None, absDir, jPlatform.get("venvDir"))
        buildSetup.absVenvExe = JoinPathIfValid(None, absDir, jPlatform.get("venvExe"))
        jMachine: dict = jPlatform.get(machine)

        if jMachine:
            buildSetup.absPythonExe = JoinPathIfValid(None, absDir, jMachine.get("pythonExe"))
            jPackages: list[str] = jMachine.get("packages")

            if jPackages:
                jPackage: str
                for jPackage in jPackages:
                    package = PyPackage()
                    package.absWhl = JoinPathIfValid(None, absDir, jPackage)
                    buildSetup.packages.append(package)

    return buildSetup


def __MakeBuildStepFromDict(jStep: dict, absDir: str) -> BuildStep:
    buildStep = BuildStep()
    buildStep.absDir = absDir
    buildStep.name = jStep.get("name")
    buildStep.config = jStep.get("config")
    jSetup: dict = jStep.get("setup")
    if jSetup:
        buildStep.setup = __MakeBuildSetupFromDict(jSetup, absDir)

    return buildStep


def __MakeBuildStepsFromJson(jsonFile: JsonFile) -> BuildStepsT:
    buildStep: BuildStep
    buildSteps = BuildStepsT()
    jBuild: dict = jsonFile.data.get("build")

    if jBuild:
        jsonDir: str = os.path.dirname(jsonFile.path)
        jSteps: list = jBuild.get("steps")
        jStep: dict

        if jSteps:
            for jStep in jSteps:
                buildStep = __MakeBuildStepFromDict(jStep, jsonDir)
                buildSteps.append(buildStep)

    for buildStep in buildSteps:
        buildStep.VerifyTypes()
        buildStep.Normalize()
        buildStep.VerifyValues()

    return buildSteps


def __Run(exec: str, *args) -> None:
    strArgs: list[str] = [exec]
    for arg in args:
        if str(arg):
            strArgs.append(str(arg))
    subprocess.run(args=strArgs, check=True)


def __RunAndCapture(exec: str, *args) -> str:
    strArgs: list[str] = [exec]
    for arg in args:
        if str(arg):
            strArgs.append(str(arg))
    outputBytes: bytes = subprocess.run(args=strArgs, check=True, capture_output=True).stdout
    outputStr: str = outputBytes.decode(sys.stdout.encoding)
    outputStr = outputStr.strip("\r\n")
    return outputStr


def __CreateVenv(buildStep: BuildStep) -> None:
    print(f"Create venv for '{buildStep.name}' ...")
    __Run(buildStep.setup.absPythonExe, "-m", "venv", buildStep.setup.absVenvDir)


def __InstallPackages(buildStep: BuildStep) -> None:
    print(f"Install packages for '{buildStep.name}' ...")
    package: PyPackage
    name: str

    for package in buildStep.setup.packages:
        __Run(buildStep.setup.absVenvExe, "-m", "pip", "install", package.AbsWhl(), "--no-index", "--find-links", package.AbsDir())

    for name in buildStep.setup.pipInstalls:
        __Run(buildStep.setup.absVenvExe, "-m", "pip", "install", name)


def __RunPoetry(buildStep: BuildStep) -> None:
    print(f"Run {buildStep.name} ...")

    workDir: str = os.getcwd()
    projDir: str = buildStep.MakeAbsPath(buildStep.config.get("projDir"))

    ChangeDir(projDir)

    try:
        # There is a bug in Poetry where it will not install packages into the virtual env,
        # if the virtual env was created freshly during "poetry install" command.
        # To trigger virtual env first, run innocent "poetry run python -V" here.
        __Run(buildStep.setup.absVenvExe, "-m", "poetry", "run", "python", "-V")
        # Install packages into Poetry's virtual env.
        __Run(buildStep.setup.absVenvExe, "-m", "poetry", "install")
        # Get virtual env path created by poetry.
        venvDir: str = __RunAndCapture(buildStep.setup.absVenvExe, "-m", "poetry", "env", "info", "--path")
        print(f"Poetry created venv '{venvDir}'")
    finally:
        ChangeDir(workDir)


def __RunPyInstaller(buildStep: BuildStep) -> None:
    print(f"Run {buildStep.name} ...")

    config: dict = buildStep.config

    workDir: str = os.getcwd()
    exeName: str = config.get("exeName")
    codeDir: str = buildStep.MakeAbsPath(config.get("codeDir"))
    codeFile: str = config.get("codeFile")
    distDir: str = buildStep.MakeAbsPath(config.get("distDir"))
    buildDir: str = buildStep.MakeAbsPath(config.get("buildDir"))
    makeArchive: bool = config.get("makeArchive")
    archiveDir: str = buildStep.MakeAbsPath(config.get("archiveDir"))
    rawImportDirs: list[str] = config.get("importDirs")
    rawDataFiles: list[dict] = config.get("dataFiles")
    pathsArgs = list[str]()
    addDataArgs = list[str]()

    rawImportDir: str
    for rawImportDir in rawImportDirs:
        dir: str = buildStep.MakeAbsPath(rawImportDir)
        pathsArgs.append("--paths")
        pathsArgs.append(dir)

    rawDataFile: dict
    for rawDataFile in rawDataFiles:
        src: str = buildStep.MakeAbsPath(rawDataFile.get("src"))
        dst: str = os.path.normpath(rawDataFile.get("dst"))
        addDataArgs.append("--add-data")
        addDataArgs.append(f"{src}{os.pathsep}{dst}")

    ChangeDir(codeDir)

    try:
        __Run(buildStep.setup.absVenvExe, "-m", "PyInstaller", codeFile,
            "--name", exeName,
            "--distpath", distDir,
            "--workpath", buildDir,
            "--specpath", buildDir,
            "--clean",
            "--onedir",
            "--noconfirm",
            *pathsArgs,
            *addDataArgs)
    finally:
        ChangeDir(workDir)

    postDeleteFiles: list[str] = config.get("postDeleteFiles")
    if postDeleteFiles:
        for file in postDeleteFiles:
            absFile: str = buildStep.MakeAbsPath(file)
            print("Delete '{absFile}'")
            DeleteFileOrPath(absFile)

    if makeArchive:
        try:
            versionScript: str = config.get("codeDir") + ".__version__"
            versionModule = importlib.import_module(versionScript)
            outBaseName: str = exeName + "_v" + versionModule.__version__
        except ImportError:
            outBaseName: str = exeName

        __BuildArchives(inDir=distDir, outDir=archiveDir, outBaseName=outBaseName)


def __BuildArchives(inDir: str, outDir: str, outBaseName: str) -> None:
    print(f"Create archives in '{outDir}' ...")

    os.makedirs(outDir, exist_ok=True)

    absBaseName = os.path.join(outDir, outBaseName)
    x7z: str = os.path.join(GetAbsFileDir(__file__), "7z.exe")

    if os.name == "nt" and os.path.isfile(x7z):
        x7zInDir: str = os.path.join(inDir, "*")
        DeleteFileOrPath(absBaseName + ".7z")
        DeleteFileOrPath(absBaseName + ".zip")
        __Run(x7z, "a", "-t7z", "-mx9", absBaseName + ".7z", x7zInDir)
        __Run(x7z, "a", "-tzip", "-mx9", absBaseName + ".zip", x7zInDir)
        GenerateHashFiles(absBaseName + ".7z")
        GenerateHashFiles(absBaseName + ".zip")
    else:
        shutil.make_archive(base_name=absBaseName, format="zip", root_dir=inDir)
        shutil.make_archive(base_name=absBaseName, format="gztar", root_dir=inDir)
        GenerateHashFiles(absBaseName + ".zip")
        GenerateHashFiles(absBaseName + ".gztar")


def Process(buildStep: BuildStep) -> None:
    __CreateVenv(buildStep)
    __InstallPackages(buildStep)

    if buildStep.name == "poetry":
        __RunPoetry(buildStep)
    elif buildStep.name == "PyInstaller":
        __RunPyInstaller(buildStep)


def Main() -> None:
    startTimer = timer()

    buildJson = JsonFile(__MakeBuildJsonPath())
    buildSteps: BuildStepsT = __MakeBuildStepsFromJson(buildJson)
    buildStep: BuildStep

    for buildStep in buildSteps:
        Process(buildStep)

    endTimer = timer()
    print("Build completed in", endTimer - startTimer, "seconds")


if __name__ == "__main__":
    Main()
