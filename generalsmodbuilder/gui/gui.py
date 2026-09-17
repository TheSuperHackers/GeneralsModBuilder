import os
import sys
import time
import threading
import traceback
from tkinter import *
from tkinter import filedialog
from tkinter.ttk import *
# These carry the bootstyle option that the palette is applied through.
from ttkbootstrap import Button, Checkbutton, Progressbar, Scrollbar
from typing import Callable
from generalsmodbuilder import util
from generalsmodbuilder.__version__ import VERSIONSTR
from generalsmodbuilder.build.engine import BuildEngine
from generalsmodbuilder.buildfunctions import CreateJsonFileList, RunWithConfig
from generalsmodbuilder.data.bundles import BundlePack, Bundles, AddBundlePacksFromJsons
from generalsmodbuilder.data.common import FinalizeParsedData
from generalsmodbuilder.data.runner import UserRunner, JoinGameExeArgs, SplitGameExeArgs
from generalsmodbuilder.gui.layout import (
    EnableDpiAwareness, GAP, MARGIN, Section)
from generalsmodbuilder.gui.operations import OPERATIONS, Operation
from generalsmodbuilder.gui.status import (
    ABORTING, IDLE, RUNNING, FormatStatusText, StatusStyle)
from generalsmodbuilder.gui.theme import (
    ACTION_STYLE, ApplyTheme, FIELD, FONT, FOREGROUND, QUIET_STYLE,
    SMALL_BUTTON_PADDING, TEAL)
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
    activity: str

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
    statusDot: Label
    statusLabel: Label
    progressBar: Progressbar


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
        self.activity = ""
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
        EnableDpiAwareness()
        window = Tk()
        window.title(f"Generals Mod Builder v{VERSIONSTR} by The Super Hackers")
        window.geometry('880x520')
        window.minsize(760, 460)
        ApplyTheme(window)
        iconFile: str =  Gui._MakeIconFilePath("icon.png")
        Gui._AddIconToWindow(window, iconFile)
        return window


    def _CreateMainWindowElements(self, window: Tk) -> None:
        header = Frame(window, padding=(MARGIN, MARGIN, MARGIN, 2))
        header.pack(fill=X)
        Label(header, text="GENERALS MOD BUILDER", style="Title.TLabel").pack(side=LEFT)
        Label(header, text=f"v{VERSIONSTR}   The Super Hackers", style="Dim.TLabel").pack(
            side=LEFT, padx=(8, 0), pady=(4, 0))

        self._CreateStatusBar(window)

        content = Frame(window, padding=(MARGIN, 4, MARGIN, 0))
        content.pack(fill=BOTH, expand=True)

        self._CreateGameSettings(content)
        self._CreateColumns(content)


    def _CreateStatusBar(self, window: Tk) -> None:
        bar = Frame(window, padding=(MARGIN, 4, MARGIN, MARGIN))
        bar.pack(fill=X, side=BOTTOM)

        self.statusDot = Label(bar, text="●", style="Ok.TLabel")
        self.statusDot.pack(side=LEFT)
        self.statusLabel = Label(bar, text="", style="Dim.TLabel")
        self.statusLabel.pack(side=LEFT)
        self.progressBar = Progressbar(bar, mode="indeterminate", length=150, bootstyle="warning")

        self.abortButton = Button(
            bar, text="Abort", command=lambda: self._Abort(),
            bootstyle=ACTION_STYLE, padding=(14, 2))
        self.abortButton.pack(side=RIGHT)


    def _CreateGameSettings(self, parent: Frame) -> None:
        holder, body, _ = Section(parent, "Game launch settings")
        holder.pack(fill=X)
        body.columnconfigure(1, weight=1)

        Gui._AddGameSettingRow(body, 0, "Install path", self.gameInstallPath, self._BrowseGameInstallPath)
        Gui._AddGameSettingRow(body, 1, "Executable", self.gameExeFile)
        Gui._AddGameSettingRow(body, 2, "Arguments", self.gameExeArgs)


    def _CreateColumns(self, parent: Frame) -> None:
        columns = Frame(parent)
        columns.pack(fill=BOTH, expand=True, pady=(GAP, 0))
        for index in range(4):
            columns.columnconfigure(index, weight=1, uniform="column")
        columns.rowconfigure(0, weight=1)

        self._CreateOptions(columns)
        self._CreateBundlePacks(columns)
        self._CreateSequence(columns)
        self._CreateActions(columns)


    def _CreateOptions(self, parent: Frame) -> None:
        holder, body, _ = Section(parent, "Options")
        holder.grid(row=0, column=0, sticky=NSEW, padx=(0, GAP))

        options = (
            ("Auto Clear Console", self.clearConsole),
            ("Print Config", self.printConfig),
            ("Verbose Logging", self.verboseLogging),
            ("Multi Processing", self.multiProcessing),
        )
        for text, variable in options:
            Checkbutton(body, text=text, variable=variable, bootstyle="warning").pack(anchor=W, pady=1)


    def _CreateBundlePacks(self, parent: Frame) -> None:
        holder, body, buttons = Section(
            parent, "Bundle packs", pad=0,
            trailing=[("Refresh", lambda: self._StartWorkThread(self._PopulateBundlePackList))])
        holder.grid(row=0, column=1, sticky=NSEW, padx=(0, GAP))
        self.bundlePackRefreshButton = buttons[0]

        # The list box is a classic tk widget that the theme does not reach.
        self.bundlePackList = Listbox(
            body, selectmode='multiple', activestyle='none', relief='flat', borderwidth=0,
            font=FONT, bg=FIELD, fg=FOREGROUND, selectbackground=TEAL,
            selectforeground="#FFFFFF", highlightthickness=0)
        self.bundlePackList.pack(side=LEFT, fill=BOTH, expand=True)

        scrollbar = Scrollbar(body, orient=VERTICAL, command=self.bundlePackList.yview,
                              bootstyle="secondary-round")
        scrollbar.pack(side=RIGHT, fill=Y)
        self.bundlePackList.configure(yscrollcommand=scrollbar.set)


    def _CreateSequence(self, parent: Frame) -> None:
        holder, body, _ = Section(parent, "Sequence execution")
        holder.grid(row=0, column=2, sticky=NSEW, padx=(0, GAP))

        for operation in OPERATIONS:
            Checkbutton(
                body, text=operation.label, variable=self.sequenceVars[operation.runKwarg],
                bootstyle="warning").pack(anchor=W, pady=1)

        self.executeButton = Button(
            body, text="Execute sequence", bootstyle=ACTION_STYLE,
            command=lambda: self._StartWorkThread(self._Execute))
        self.executeButton.pack(fill=X, pady=(6, 0))


    def _CreateActions(self, parent: Frame) -> None:
        holder, body, _ = Section(parent, "Single actions")
        holder.grid(row=0, column=3, sticky=NSEW)

        self.actionButtons = list()
        for operation in OPERATIONS:
            button = Button(
                body, text=operation.label, bootstyle=ACTION_STYLE,
                command=lambda op=operation: self._StartWorkThread(lambda: self._RunOperation(op)))
            button.pack(fill=X, pady=1)
            self.actionButtons.append(button)


    @staticmethod
    def _AddGameSettingRow(frame: Frame, row: int, text: str, var: StringVar, browse: Callable = None) -> None:
        Label(frame, text=text, width=11).grid(row=row, column=0, sticky=W, pady=1)
        Entry(frame, textvariable=var, font=FONT).grid(row=row, column=1, sticky=EW, pady=1, padx=(4, 0))
        if browse != None:
            Button(frame, text="Browse...", command=browse, bootstyle=QUIET_STYLE,
                   padding=SMALL_BUTTON_PADDING).grid(row=row, column=2, padx=(6, 0))



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
        self.statusDot = None
        self.statusLabel = None
        self.progressBar = None


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
            self._SetStatus(IDLE)


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

        self._DoWork(Run, "Execute sequence")


    def _RunOperation(self, operation: Operation) -> None:
        def Run() -> None:
            arguments: dict = self._MakeRunArguments(operation.usesBuildContext)
            arguments[operation.runKwarg] = True
            RunWithConfig(**arguments)

        self._DoWork(Run, operation.label)


    def _DoWork(self, function: Callable, activity: str) -> None:
        self.activity = activity
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


    def _SetStatus(self, state: str, activity: str = "") -> None:
        if self.statusLabel == None:
            return

        self.statusDot["style"] = StatusStyle(state)
        self.statusLabel["text"] = "  " + FormatStatusText(
            state, self.bundlePackList.size(), len(self.bundlePackList.curselection()), activity)

        if state == RUNNING:
            self.progressBar.pack(side=LEFT, padx=(10, 0))
            self.progressBar.start(12)
        elif state == IDLE:
            self.progressBar.stop()
            self.progressBar.pack_forget()


    def _OnWorkBegin(self) -> None:
        with self.buildEngineLock:
            self.buildEngine = BuildEngine()
            self.buildAndInstallList = Gui._GetBundlePackNamesFromList(self.bundlePackList)

        self._SaveUserSettings()

        if self.clearConsole.get():
            Gui._ClearConsole()

        with self.mainWindowLock:
            self._SetJobElementsState("disabled")
            self._SetStatus(RUNNING, self.activity)

        self._StartAbortThread()


    def _OnWorkEnd(self) -> None:
        with self.buildEngineLock:
            self.buildEngine.Shutdown()
            self.buildEngine = None

        self.abortThread.join()
        self.abortThread = None

        with self.mainWindowLock:
            self._SetJobElementsState("normal")
            self._SetStatus(IDLE)


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
        with self.mainWindowLock:
            self._SetStatus(ABORTING, self.activity)
        with self.buildEngineLock:
            self.buildEngine.Abort()
