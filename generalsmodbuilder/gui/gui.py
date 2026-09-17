import os
import sys
import time
import threading
import traceback
from tkinter import *
from tkinter import filedialog
from tkinter.ttk import *
from typing import Callable
from generalsmodbuilder import util
from generalsmodbuilder.__version__ import VERSIONSTR
from generalsmodbuilder.build.engine import BuildEngine
from generalsmodbuilder.buildfunctions import CreateJsonFileList, RunWithConfig
from generalsmodbuilder.data.bundles import BundlePack, Bundles, AddBundlePacksFromJsons
from generalsmodbuilder.data.common import FinalizeParsedData
from generalsmodbuilder.data.runner import UserRunner, JoinGameExeArgs, SplitGameExeArgs
from generalsmodbuilder.gui.operations import OPERATIONS, Operation
from generalsmodbuilder.usersettings import (
    GetUserSettingsFile, LoadUserRunner, MergeUserRunners, SaveUserRunner)
from generalsmodbuilder.util import JsonFile


class Gui:
    workThread: threading.Thread
    abortThread: threading.Thread
    buildEngine: BuildEngine
    buildEngineLock: threading.RLock
    mainWindowLock: threading.RLock

    configPaths: list[str]
    buildAndInstallList: list[str]
    debug: bool
    toolsRootDir: str

    sequenceVars: dict[str, BooleanVar]

    gameInstallPath: StringVar
    gameExeFile: StringVar
    gameExeArgs: StringVar

    printConfig: BooleanVar
    clearConsole: BooleanVar
    verboseLogging: BooleanVar
    multiProcessing: BooleanVar

    bundlePackList: Listbox
    executeButton: Button
    actionButtons: list[Button]
    abortButton: Button
    bundlePackRefreshButton: Button


    def __init__(self):
        self.workThread = None
        self.abortThread = None
        self.buildEngine = None
        self.buildEngineLock = threading.RLock()
        self.mainWindowLock = threading.RLock()
        self.configPaths = None
        self.buildAndInstallList = None
        self.debug = False
        self.toolsRootDir = None
        self._ClearMainWindowElements()


    def RunWithConfig(self,
            configPaths: list[str] = list(),
            installList: list[str] = list(),
            buildList: list[str] = list(),
            makeChangeLog: bool = False,
            clean: bool = False,
            build: bool = False,
            release: bool = False,
            install: bool = False,
            uninstall: bool = False,
            run: bool = False,
            debug: bool = False,
            printConfig: bool = False,
            verboseLogging: bool = False,
            multiProcessing: bool = False,
            toolsRootDir: str = None,
            userRunner: UserRunner = None):

        self.configPaths = configPaths
        self.buildAndInstallList = installList
        self.buildAndInstallList.extend(buildList)
        self.debug = debug
        self.toolsRootDir = toolsRootDir

        mainWindow: Tk = Gui._CreateMainWindow()

        initialSequence: dict[str, bool] = {
            "makeChangeLog": makeChangeLog,
            "clean": clean,
            "build": build,
            "release": release,
            "install": install,
            "uninstall": uninstall,
            "run": run,
        }
        self.sequenceVars = {
            op.runKwarg: BooleanVar(mainWindow, value=initialSequence[op.runKwarg])
            for op in OPERATIONS}

        self.printConfig = BooleanVar(mainWindow, value=printConfig)
        self.clearConsole = BooleanVar(mainWindow, value=True)
        self.verboseLogging = BooleanVar(mainWindow, value=verboseLogging)
        self.multiProcessing = BooleanVar(mainWindow, value=multiProcessing)

        settings: UserRunner = MergeUserRunners(
            userRunner if userRunner != None else UserRunner(), LoadUserRunner(GetUserSettingsFile()))
        self.gameInstallPath = StringVar(mainWindow, value=settings.absGameInstallDir)
        self.gameExeFile = StringVar(mainWindow, value=settings.relGameExeFile)
        self.gameExeArgs = StringVar(
            mainWindow, value=JoinGameExeArgs(settings.gameExeArgs) if settings.gameExeArgs != None else "")

        self._CreateMainWindowElements(mainWindow)
        self._SetAbortElementsState("disabled")
        self._StartWorkThread(self._PopulateBundlePackList)

        mainWindow.mainloop()

        self._SaveUserSettings()

        with self.mainWindowLock:
            self._ClearMainWindowElements()

        self.workThread.join()


    @staticmethod
    def _MakeIconFilePath(iconName: str) -> str:
        iconFile: str = os.path.join(util.g_appDir, "gui", iconName)
        return iconFile


    @staticmethod
    def _AddIconToWindow(window: Tk, iconFile: str) -> None:
        if os.path.isfile(iconFile):
            photoImage = PhotoImage(file = iconFile)
            window.wm_iconphoto(False, photoImage)


    @staticmethod
    def _CreateMainWindow() -> Tk:
        window = Tk()
        window.title(f"Generals Mod Builder v{VERSIONSTR} by The Super Hackers")
        window.geometry('700x430')
        window.resizable(0, 0)
        iconFile: str =  Gui._MakeIconFilePath("icon.png")
        Gui._AddIconToWindow(window, iconFile)
        return window


    def _CreateMainWindowElements(self, window: Tk) -> None:
        buttonWidth = 20
        checkboxWidth = 18
        listboxWidth = 21

        mainFrame = Frame(window, padding=10)
        mainFrame.pack()

        frame1000 = Frame(mainFrame)
        frame1000.grid(row=0, column=0, sticky='n')
        frame0100 = Frame(mainFrame)
        frame0100.grid(row=0, column=1, sticky='n')
        frame0010 = Frame(mainFrame)
        frame0010.grid(row=0, column=2, sticky='n')
        frame0001 = Frame(mainFrame)
        frame0001.grid(row=0, column=3, sticky='n')

        executeLabel = Label(frame0100, text = "Sequence execution")
        executeLabel.pack(anchor=CENTER)
        executeFrame = Frame(frame0100, padding=10, relief='solid')
        executeFrame.pack(padx=5, pady=5)

        optionsLabel = Label(frame0001, text = "Options")
        optionsLabel.pack(anchor=CENTER)
        optionsFrame = Frame(frame0001, padding=10, relief='solid')
        optionsFrame.pack(padx=5, pady=5)

        actionsLabel = Label(frame0010, text = "Single actions")
        actionsLabel.pack(anchor=CENTER)
        actionsFrame = Frame(frame0010, padding=10, relief='solid')
        actionsFrame.pack(padx=5, pady=5)

        bundlePackLabel = Label(frame1000, text = "Bundle Pack list")
        bundlePackLabel.pack(anchor=CENTER)
        bundlePackFrame = Frame(frame1000, padding=10, relief='solid')
        bundlePackFrame.pack(padx=5, pady=5)

        # Execute Frame

        for operation in OPERATIONS:
            check = Checkbutton(
                executeFrame,
                width=checkboxWidth,
                text=operation.label,
                var=self.sequenceVars[operation.runKwarg])
            check.pack(anchor=W)

        self.executeButton = Button(executeFrame, width=buttonWidth, text="Execute", command=lambda:self._StartWorkThread(self._Execute))
        self.executeButton.pack(anchor=W)

        # Options Frame

        clearLogCheck = Checkbutton(optionsFrame, width = checkboxWidth, text='Auto Clear Console', var=self.clearConsole)
        clearLogCheck.pack(anchor=W)

        printConfig = Checkbutton(optionsFrame, width = checkboxWidth, text='Print Config', var=self.printConfig)
        printConfig.pack(anchor=W)

        verboseLogging = Checkbutton(optionsFrame, width = checkboxWidth, text='Verbose Logging', var=self.verboseLogging)
        verboseLogging.pack(anchor=W)

        multiProcessing = Checkbutton(optionsFrame, width = checkboxWidth, text='Multi Processing', var=self.multiProcessing)
        multiProcessing.pack(anchor=W)

        # Actions Frame

        self.actionButtons = list()
        for operation in OPERATIONS:
            button = Button(
                actionsFrame,
                width=buttonWidth,
                text=operation.label,
                command=lambda op=operation: self._StartWorkThread(lambda: self._RunOperation(op)))
            button.pack(anchor=W)
            self.actionButtons.append(button)

        self.abortButton = Button(actionsFrame, width=buttonWidth, text="Abort", command=lambda:self._Abort())
        self.abortButton.pack(anchor=W)

        # Bundle Pack Frame

        self.bundlePackList = Listbox(bundlePackFrame, width=listboxWidth, relief='flat', selectmode='multiple')
        self.bundlePackList.pack(anchor=W)

        self.bundlePackRefreshButton = Button(bundlePackFrame, width=buttonWidth, text="Refresh", command=lambda:self._StartWorkThread(self._PopulateBundlePackList))
        self.bundlePackRefreshButton.pack(anchor=W)

        # Game Launch Settings Frame

        frame1111 = Frame(mainFrame)
        frame1111.grid(row=1, column=0, columnspan=4)

        gameLabel = Label(frame1111, text = "Game launch settings")
        gameLabel.pack(anchor=CENTER)
        gameFrame = Frame(frame1111, padding=10, relief='solid')
        gameFrame.pack(padx=5, pady=5)

        Gui._AddGameSettingRow(gameFrame, 0, "Game install path", self.gameInstallPath, self._BrowseGameInstallPath)
        Gui._AddGameSettingRow(gameFrame, 1, "Game exe file", self.gameExeFile)
        Gui._AddGameSettingRow(gameFrame, 2, "Game exe args", self.gameExeArgs)


    @staticmethod
    def _AddGameSettingRow(frame: Frame, row: int, text: str, var: StringVar, browse: Callable = None) -> None:
        Label(frame, text=text, width=17).grid(row=row, column=0, sticky=W, pady=2)
        Entry(frame, textvariable=var, width=70).grid(row=row, column=1, sticky=W, pady=2)
        if browse != None:
            Button(frame, text="Browse...", width=10, command=browse).grid(row=row, column=2, padx=5)


    def _BrowseGameInstallPath(self) -> None:
        directory: str = filedialog.askdirectory(initialdir=self.gameInstallPath.get())
        if directory:
            self.gameInstallPath.set(os.path.normpath(directory))


    def _MakeUserRunner(self) -> UserRunner:
        gameInstallPath: str = self.gameInstallPath.get().strip()
        gameExeFile: str = self.gameExeFile.get().strip()
        gameExeArgs: str = self.gameExeArgs.get().strip()

        if gameInstallPath:
            gameInstallPath = os.path.abspath(gameInstallPath)

        if gameExeArgs:
            gameExeArgs = SplitGameExeArgs(gameExeArgs)
        else:
            gameExeArgs = None

        userRunner = UserRunner(
            absGameInstallDir=gameInstallPath,
            relGameExeFile=gameExeFile,
            gameExeArgs=gameExeArgs)

        FinalizeParsedData(userRunner)
        return userRunner


    def _SaveUserSettings(self) -> None:
        if self.gameInstallPath == None:
            return
        try:
            SaveUserRunner(
                GetUserSettingsFile(),
                self.gameInstallPath.get().strip(),
                self.gameExeFile.get().strip(),
                self.gameExeArgs.get().strip())
        except Exception as error:
            print(f"User settings are not saved: {error}")


    def _ClearMainWindowElements(self) -> None:
        self.sequenceVars = None
        self.gameInstallPath = None
        self.gameExeFile = None
        self.gameExeArgs = None
        self.printConfig = None
        self.clearConsole = None
        self.verboseLogging = None
        self.multiProcessing = None
        self.bundlePackList = None
        self.executeButton = None
        self.actionButtons = None
        self.abortButton = None
        self.bundlePackRefreshButton = None


    @staticmethod
    def _GetBundlePackNamesFromList(bundlePackList: Listbox) -> list[str]:
        bundlePackNames = list()
        selections: tuple = bundlePackList.curselection()
        selection: int
        for selection in selections:
            name: str = bundlePackList.get(selection)
            bundlePackNames.append(name)
        return bundlePackNames


    @staticmethod
    def _GetBundlePackNamesFromConfig(configPaths: list[str]) -> list[str]:
        bundlePackNames = list()
        jsonFiles: list[JsonFile] = CreateJsonFileList(configPaths)
        bundles = Bundles()
        AddBundlePacksFromJsons(jsonFiles, bundles)
        bundlePack: BundlePack
        for bundlePack in bundles.packs:
            bundlePackNames.append(bundlePack.name)
        return bundlePackNames


    def _PopulateBundlePackList(self) -> None:
        with self.mainWindowLock:
            self._SetJobElementsState("disabled")

        bundlePackNames: list[str] = Gui._GetBundlePackNamesFromConfig(self.configPaths)
        self.bundlePackList.delete(0, self.bundlePackList.size())
        self.bundlePackList.insert(0, *bundlePackNames)
        name1: str
        name2: str
        for name1 in self.buildAndInstallList:
            for index,name2 in enumerate(bundlePackNames):
                if name1 == name2:
                    self.bundlePackList.selection_set(index)

        with self.mainWindowLock:
            self._SetJobElementsState("normal")


    @staticmethod
    def _ClearConsole() -> None:
        if sys.stdout.isatty():
            os.system('cls||clear')


    def _MakeRunArguments(self, usesBuildContext: bool) -> dict:
        """
        The arguments of one build job. They are read when the job starts, not when the
        button is pressed, because the bundle pack selection and the engine are made by
        _OnWorkBegin.
        """
        arguments = dict(
            configPaths=self.configPaths,
            printConfig=self.printConfig.get(),
            verboseLogging=self.verboseLogging.get(),
            multiProcessing=self.multiProcessing.get())

        if usesBuildContext:
            arguments.update(
                installList=self.buildAndInstallList,
                buildList=self.buildAndInstallList,
                toolsRootDir=self.toolsRootDir,
                userRunner=self._MakeUserRunner(),
                engine=self.buildEngine)

        return arguments


    def _Execute(self) -> None:
        def Run() -> None:
            arguments: dict = self._MakeRunArguments(usesBuildContext=True)
            for operation in OPERATIONS:
                arguments[operation.runKwarg] = self.sequenceVars[operation.runKwarg].get()
            RunWithConfig(**arguments)

        self._DoWork(Run)


    def _RunOperation(self, operation: Operation) -> None:
        def Run() -> None:
            arguments: dict = self._MakeRunArguments(operation.usesBuildContext)
            arguments[operation.runKwarg] = True
            RunWithConfig(**arguments)

        self._DoWork(Run)


    def _DoWork(self, function: Callable) -> None:
        self._OnWorkBegin()

        if self.debug:
            function()
        else:
            try:
                function()
            except Exception:
                print("ERROR CALLSTACK")
                traceback.print_exc()

        self._OnWorkEnd()


    def _OnWorkBegin(self) -> None:
        with self.buildEngineLock:
            self.buildEngine = BuildEngine()
            self.buildAndInstallList = Gui._GetBundlePackNamesFromList(self.bundlePackList)

        self._SaveUserSettings()

        if self.clearConsole.get():
            Gui._ClearConsole()

        with self.mainWindowLock:
            self._SetJobElementsState("disabled")

        self._StartAbortThread()


    def _OnWorkEnd(self) -> None:
        with self.buildEngineLock:
            self.buildEngine.Shutdown()
            self.buildEngine = None

        self.abortThread.join()
        self.abortThread = None

        with self.mainWindowLock:
            self._SetJobElementsState("normal")


    def _SetJobElementsState(self, state: str) -> None:
        if self.executeButton != None:
            self.executeButton["state"] = state
            self.bundlePackRefreshButton["state"] = state
            button: Button
            for button in self.actionButtons:
                button["state"] = state


    def _SetAbortElementsState(self, state: str) -> None:
        if self.abortButton != None:
            self.abortButton["state"] = state


    def _StartWorkThread(self, func: Callable) -> None:
        self.workThread = threading.Thread(target=func)
        self.workThread.start()


    def _StartAbortThread(self) -> None:
        self.abortThread = threading.Thread(target=self._AbortUpdateLoop)
        self.abortThread.start()


    def _AbortUpdateLoop(self) -> None:
        canAbort: bool = False
        wasAbort: bool = canAbort
        while True:
            with self.buildEngineLock:
                if self.buildEngine == None:
                    with self.mainWindowLock:
                        self._SetAbortElementsState("disabled")
                    break
                canAbort = self.buildEngine.CanAbort()
                if canAbort != wasAbort:
                    if canAbort:
                        with self.mainWindowLock:
                            self._SetAbortElementsState("enabled")
                    else:
                        with self.mainWindowLock:
                            self._SetAbortElementsState("disabled")
                wasAbort = canAbort

            time.sleep(0.1)

        return


    def _Abort(self) -> None:
        with self.buildEngineLock:
            self.buildEngine.Abort()
