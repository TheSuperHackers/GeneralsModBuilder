import os
import queue
import sys
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
    EnableDpiAwareness, GAP, MARGIN, Section, Tooltip)
from generalsmodbuilder.gui.logpane import LogPane, StreamTee
from generalsmodbuilder.gui.operations import OPERATIONS, Operation
from generalsmodbuilder.gui.packlist import PackList
from generalsmodbuilder.gui.status import (
    ABORTING, IDLE, RUNNING, FormatStatusText, StatusStyle)
from generalsmodbuilder.gui.theme import (
    ACTION_STYLE, ApplyTheme, FONT, QUIET_STYLE, SMALL_BUTTON_PADDING)
from generalsmodbuilder.usersettings import (
    GetUserSettingsFile, LoadUserRunner, MergeUserRunners, SaveUserRunner)
from generalsmodbuilder.util import JsonFile


PUMP_INTERVAL_MS = 50


class Gui:
    workThread: threading.Thread
    buildEngine: BuildEngine
    buildEngineLock: threading.RLock
    mainWindow: Tk
    uiQueue: queue.Queue
    logQueue: queue.Queue
    logPane: LogPane
    checkedPackNames: list[str]

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

    bundlePackList: PackList
    executeButton: Button
    actionButtons: list[Button]
    abortButton: Button
    bundlePackRefreshButton: Button
    statusDot: Label
    statusLabel: Label
    progressBar: Progressbar


    def __init__(self):
        self.workThread = None
        self.buildEngine = None
        self.buildEngineLock = threading.RLock()
        self.mainWindow = None
        self.uiQueue = queue.Queue()
        self.logQueue = queue.Queue()
        self.checkedPackNames = list()
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
        self.mainWindow = mainWindow

        initialSequence: dict[str, bool] = {
            "makeChangeLog": makeChangeLog,
            "clean": clean,
            "build": build,
            "release": release,
            "install": install,
            "uninstall": uninstall,
            "run": run,
        }
        settings: UserRunner = MergeUserRunners(
            userRunner if userRunner != None else UserRunner(), LoadUserRunner(GetUserSettingsFile()))

        self._CreateMainWindowVariables(
            mainWindow, initialSequence, printConfig, verboseLogging, multiProcessing, settings)
        self._CreateMainWindowElements(mainWindow)
        self._SetAbortElementsState("disabled")
        self._StartWorkThread(self._PopulateBundlePackList)

        # The console keeps receiving everything, the pane gets a copy.
        originalOut, originalErr = sys.stdout, sys.stderr
        sys.stdout = StreamTee(originalOut, self.logQueue)
        sys.stderr = StreamTee(originalErr, self.logQueue)
        try:
            mainWindow.after(PUMP_INTERVAL_MS, self._PumpUi)
            mainWindow.mainloop()
        finally:
            sys.stdout, sys.stderr = originalOut, originalErr

        self._SaveUserSettings()
        self._ClearMainWindowElements()
        self.mainWindow = None

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
        window.geometry('880x730')
        window.minsize(760, 560)
        ApplyTheme(window)
        iconFile: str =  Gui._MakeIconFilePath("icon.png")
        Gui._AddIconToWindow(window, iconFile)
        return window


    def _CreateMainWindowVariables(self,
            window: Tk,
            initialSequence: dict[str, bool],
            printConfig: bool,
            verboseLogging: bool,
            multiProcessing: bool,
            settings: UserRunner) -> None:

        self.sequenceVars = {
            op.runKwarg: BooleanVar(window, value=initialSequence[op.runKwarg])
            for op in OPERATIONS}

        self.printConfig = BooleanVar(window, value=printConfig)
        self.clearConsole = BooleanVar(window, value=True)
        self.verboseLogging = BooleanVar(window, value=verboseLogging)
        self.multiProcessing = BooleanVar(window, value=multiProcessing)

        self.gameInstallPath = StringVar(window, value=settings.absGameInstallDir)
        self.gameExeFile = StringVar(window, value=settings.relGameExeFile)
        self.gameExeArgs = StringVar(
            window, value=JoinGameExeArgs(settings.gameExeArgs) if settings.gameExeArgs != None else "")


    def _CreateMainWindowElements(self, window: Tk) -> None:
        header = Frame(window, padding=(MARGIN, MARGIN, MARGIN, 2))
        header.pack(fill=X)
        Label(header, text="GENERALS MOD BUILDER", style="Title.TLabel").pack(side=LEFT)
        Label(header, text=f"v{VERSIONSTR}   The Super Hackers", style="Dim.TLabel").pack(
            side=LEFT, padx=(8, 0), pady=(4, 0))

        self._CreateStatusBar(window)

        paned = PanedWindow(window, orient=VERTICAL)
        paned.pack(fill=BOTH, expand=True, padx=MARGIN, pady=(4, 0))

        content = Frame(paned)
        paned.add(content, weight=0)
        self._CreateGameSettings(content)
        self._CreateColumns(content)

        output = Frame(paned, padding=(0, GAP, 1, 0))
        paned.add(output, weight=1)
        self._CreateOutput(output)


    def _CreateOutput(self, parent: Frame) -> None:
        holder, body, _ = Section(
            parent, "Output", pad=0,
            trailing=[("Clear", lambda: self.logPane.Clear(), "Empties the output pane."),
                      ("Copy", lambda: self.logPane.Copy(), "Copies the output to the clipboard.")])
        holder.pack(fill=BOTH, expand=True)
        self.logPane = LogPane(body, self.logQueue)


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
        Tooltip(self.abortButton, "Stops the running game. A build cannot be interrupted.")


    def _CreateGameSettings(self, parent: Frame) -> None:
        holder, body, _ = Section(parent, "Game launch settings")
        holder.pack(fill=X)
        body.columnconfigure(1, weight=1)

        Gui._AddGameSettingRow(
            body, 0, "Install path", self.gameInstallPath,
            "The game folder that Install, Uninstall and Run Game work on.",
            self._BrowseGameInstallPath, "Picks the game install folder.")
        Gui._AddGameSettingRow(
            body, 1, "Executable", self.gameExeFile,
            "The game executable, relative to the install path.")
        Gui._AddGameSettingRow(
            body, 2, "Arguments", self.gameExeArgs,
            "Arguments for the game, for example -win -quickstart.")


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
            ("Auto Clear Console", self.clearConsole, "Clears the console and the output pane when a job starts."),
            ("Print Config", self.printConfig, "Prints the parsed configuration before the build runs."),
            ("Verbose Logging", self.verboseLogging, "Logs every copied file and every file hash."),
            ("Multi Processing", self.multiProcessing, "Builds files in parallel processes."),
        )
        for text, variable, hint in options:
            check = Checkbutton(body, text=text, variable=variable, bootstyle="warning")
            check.pack(anchor=W, pady=1)
            Tooltip(check, hint)


    def _CreateBundlePacks(self, parent: Frame) -> None:
        holder, body, buttons = Section(
            parent, "Bundle packs", pad=0,
            trailing=[("Refresh", lambda: self._StartWorkThread(self._PopulateBundlePackList),
                        "Reads the bundle packs from the configuration again.")])
        holder.grid(row=0, column=1, sticky=NSEW, padx=(0, GAP))
        self.bundlePackRefreshButton = buttons[0]
        self.bundlePackList = PackList(body)
        Tooltip(self.bundlePackList.tree,
                "Tick the packs to build and install. With none ticked, every pack is processed.")


    def _CreateSequence(self, parent: Frame) -> None:
        holder, body, _ = Section(parent, "Sequence execution")
        holder.grid(row=0, column=2, sticky=NSEW, padx=(0, GAP))

        for operation in OPERATIONS:
            check = Checkbutton(
                body, text=operation.label, variable=self.sequenceVars[operation.runKwarg],
                bootstyle="warning")
            check.pack(anchor=W, pady=1)
            Tooltip(check, operation.hint)

        self.executeButton = Button(
            body, text="Execute sequence", bootstyle=ACTION_STYLE,
            command=lambda: self._StartWorkThread(self._Execute))
        self.executeButton.pack(fill=X, pady=(6, 0))
        Tooltip(self.executeButton, "Runs the ticked operations, top to bottom.")


    def _CreateActions(self, parent: Frame) -> None:
        holder, body, _ = Section(parent, "Single actions")
        holder.grid(row=0, column=3, sticky=NSEW)

        self.actionButtons = list()
        for operation in OPERATIONS:
            button = Button(
                body, text=operation.label, bootstyle=ACTION_STYLE,
                command=lambda op=operation: self._StartWorkThread(lambda: self._RunOperation(op)))
            button.pack(fill=X, pady=1)
            Tooltip(button, operation.hint)
            self.actionButtons.append(button)


    @staticmethod
    def _AddGameSettingRow(frame: Frame, row: int, text: str, var: StringVar, hint: str,
                           browse: Callable = None, browseHint: str = None) -> None:
        Label(frame, text=text, width=11).grid(row=row, column=0, sticky=W, pady=1)
        entry = Entry(frame, textvariable=var, font=FONT)
        entry.grid(row=row, column=1, sticky=EW, pady=1, padx=(4, 0))
        Tooltip(entry, hint)
        if browse != None:
            button = Button(frame, text="Browse...", command=browse, bootstyle=QUIET_STYLE,
                            padding=SMALL_BUTTON_PADDING)
            button.grid(row=row, column=2, padx=(6, 0))
            Tooltip(button, browseHint)



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
        self.logPane = None


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
        self._Post(lambda: self._SetJobElementsState("disabled"))

        names: list[str] = Gui._GetBundlePackNamesFromConfig(self.configPaths)
        wanted: list[str] = list(self.buildAndInstallList)

        def Apply() -> None:
            self.bundlePackList.SetNames(names, wanted)
            self._SetJobElementsState("normal")
            self._SetStatus(IDLE)

        self._Post(Apply)


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
            state, self.bundlePackList.Count(), self.bundlePackList.CheckedCount(), activity)

        if state == RUNNING:
            self.progressBar.pack(side=LEFT, padx=(10, 0))
            self.progressBar.start(12)
        elif state == IDLE:
            self.progressBar.stop()
            self.progressBar.pack_forget()


    def _OnWorkBegin(self) -> None:
        with self.buildEngineLock:
            self.buildEngine = BuildEngine()
            self.buildAndInstallList = self.checkedPackNames

        if self.clearConsole.get():
            Gui._ClearConsole()
            self._Post(self.logPane.Clear)

        self._Post(lambda: self._SetJobElementsState("disabled"))
        self._Post(lambda: self._SetStatus(RUNNING, self.activity))


    def _OnWorkEnd(self) -> None:
        with self.buildEngineLock:
            self.buildEngine.Shutdown()
            self.buildEngine = None

        self._Post(lambda: self._SetJobElementsState("normal"))
        self._Post(lambda: self._SetStatus(IDLE))


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


    def _Post(self, action: Callable) -> None:
        """Hands widget work to the main thread. Tk must not be touched from a worker."""
        self.uiQueue.put(action)


    def _PumpUi(self) -> None:
        """The one place that touches widgets on behalf of the build threads."""
        while True:
            try:
                action: Callable = self.uiQueue.get_nowait()
            except queue.Empty:
                break
            action()

        self.logPane.Drain()
        self._UpdateAbortState()
        self._RememberCheckedPacks()
        self.mainWindow.after(PUMP_INTERVAL_MS, self._PumpUi)


    def _UpdateAbortState(self) -> None:
        with self.buildEngineLock:
            canAbort: bool = self.buildEngine != None and self.buildEngine.CanAbort()
        self._SetAbortElementsState("normal" if canAbort else "disabled")


    def _RememberCheckedPacks(self) -> None:
        """The work thread cannot read the tree, so the pump keeps the selection for it."""
        self.checkedPackNames = self.bundlePackList.CheckedNames()


    def _Abort(self) -> None:
        self._SetStatus(ABORTING, self.activity)
        with self.buildEngineLock:
            self.buildEngine.Abort()
