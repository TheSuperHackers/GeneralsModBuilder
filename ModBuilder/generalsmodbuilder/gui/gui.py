import os
import traceback
from tkinter import *
from tkinter.ttk import *
from generalsmodbuilder.__version__ import __version__
from generalsmodbuilder.buildfunctions import CreateJsonFiles, RunWithConfig
from generalsmodbuilder.data.bundles import BundlePack, Bundles, MakeBundlesFromJsons
from generalsmodbuilder.util import JsonFile


class Gui:
    configPaths: list[str]
    installList: list[str]
    clean: BooleanVar
    build: BooleanVar
    release: BooleanVar
    install: BooleanVar
    uninstall: BooleanVar
    run: BooleanVar
    printConfig: BooleanVar
    clearConsole: BooleanVar
    bundlePackList: Listbox


    def __init__(self):
        pass


    def RunWithConfig(self,
            configPaths: list[str] = list(),
            installList: list[str] = list(),
            clean: bool = False,
            build: bool = False,
            release: bool = False,
            install: bool = False,
            uninstall: bool = False,
            run: bool = False,
            printConfig: bool = False):

        mainWindow: Tk = Gui._CreateMainWindow()

        self.configPaths = configPaths
        self.installList = installList
        self.clean = BooleanVar(mainWindow, value=clean)
        self.build = BooleanVar(mainWindow, value=build)
        self.release = BooleanVar(mainWindow, value=release)
        self.install = BooleanVar(mainWindow, value=install)
        self.uninstall = BooleanVar(mainWindow, value=uninstall)
        self.run = BooleanVar(mainWindow, value=run)
        self.printConfig = BooleanVar(mainWindow, value=printConfig)
        self.clearConsole = BooleanVar(mainWindow, value=True)

        self._CreateMainWindowElements(mainWindow)

        mainWindow.mainloop()


    @staticmethod
    def _CreateMainWindow() -> Tk:
        window = Tk()
        window.title(f"Generals Mod Builder v{__version__} by The Super Hackers")
        window.geometry('660x260')
        window.resizable(0, 0)
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

        executeFrame = Frame(frame0100, padding=10, relief='solid')
        executeFrame.pack(padx=5, pady=5)

        optionsFrame = Frame(frame0001, padding=10, relief='solid')
        optionsFrame.pack(padx=5, pady=5)

        actionsFrame = Frame(frame0010, padding=10, relief='solid')
        actionsFrame.pack(padx=5, pady=5)

        bundlePackFrame = Frame(frame1000, padding=10, relief='solid')
        bundlePackFrame.pack(padx=5, pady=5)

        # Execute Frame

        executeLabel = Label(executeFrame, text = "Execute sequence")
        executeLabel.pack(anchor=W)

        cleanCheck = Checkbutton(executeFrame, width = checkboxWidth, text='Clean', var=self.clean)
        cleanCheck.pack(anchor=W)

        buildCheck = Checkbutton(executeFrame, width = checkboxWidth, text='Build', var=self.build)
        buildCheck.pack(anchor=W)

        releaseCheck = Checkbutton(executeFrame, width = checkboxWidth, text='Release', var=self.release)
        releaseCheck.pack(anchor=W)

        installCheck = Checkbutton(executeFrame, width = checkboxWidth, text='Install', var=self.install)
        installCheck.pack(anchor=W)

        runCheck = Checkbutton(executeFrame, width = checkboxWidth, text='Run Game', var=self.run)
        runCheck.pack(anchor=W)

        uninstallCheck = Checkbutton(executeFrame, width = checkboxWidth, text='Uninstall', var=self.uninstall)
        uninstallCheck.pack(anchor=W)

        executeButton = Button(executeFrame, width=buttonWidth, text="Execute", command=self._Execute)
        executeButton.pack(anchor=W)

        # Options Frame

        executeLabel = Label(optionsFrame, text = "Options")
        executeLabel.pack(anchor=W)

        clearLogCheck = Checkbutton(optionsFrame, width = checkboxWidth, text='Auto Clear Console', var=self.clearConsole)
        clearLogCheck.pack(anchor=W)

        printConfig = Checkbutton(optionsFrame, width = checkboxWidth, text='Print Config', var=self.printConfig)
        printConfig.pack(anchor=W)

        # Actions Frame

        actionsLabel = Label(actionsFrame, text = "Single actions")
        actionsLabel.pack(anchor=W)

        cleanButton = Button(actionsFrame, width=buttonWidth, text="Clean", command=self._Clean)
        cleanButton.pack(anchor=W)

        buildButton = Button(actionsFrame, width=buttonWidth, text="Build", command=self._Build)
        buildButton.pack(anchor=W)

        releaseButton = Button(actionsFrame, width=buttonWidth, text="Release", command=self._Release)
        releaseButton.pack(anchor=W)

        installButton = Button(actionsFrame, width=buttonWidth, text="Install", command=self._Install)
        installButton.pack(anchor=W)

        runButton = Button(actionsFrame, width=buttonWidth, text="Run Game", command=self._RunGame)
        runButton.pack(anchor=W)

        uninstallButton = Button(actionsFrame, width=buttonWidth, text="Uninstall", command=self._Uninstall)
        uninstallButton.pack(anchor=W)

        # Bundle Pack Frame

        bundlePackLabel = Label(bundlePackFrame, text = "Bundle Pack list")
        bundlePackLabel.pack(anchor=W)

        self.bundlePackList = Listbox(bundlePackFrame, width=listboxWidth, relief='flat', selectmode='multiple')
        self.bundlePackList.pack(anchor=W)
        self._PopulateBundlePackList()

        bundlePackRefreshButton = Button(bundlePackFrame, width=buttonWidth, text="Refresh", command=self._PopulateBundlePackList)
        bundlePackRefreshButton.pack(anchor=W)


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
        jsonFiles: list[JsonFile] = CreateJsonFiles(configPaths)
        bundles: Bundles = MakeBundlesFromJsons(jsonFiles)
        bundlePack: BundlePack
        for bundlePack in bundles.packs:
            bundlePackNames.append(bundlePack.name)
        return bundlePackNames


    def _PopulateBundlePackList(self) -> None:
        bundlePackNames: list[str] = Gui._GetBundlePackNamesFromConfig(self.configPaths)
        self.bundlePackList.delete(0, self.bundlePackList.size())
        self.bundlePackList.insert(0, *bundlePackNames)
        name1: str
        name2: str
        for name1 in self.installList:
            for index,name2 in enumerate(bundlePackNames):
                if name1 == name2:
                    self.bundlePackList.selection_set(index)


    @staticmethod
    def _ClearConsole() -> None:
        os.system('cls||clear')


    def _Execute(self) -> None:
        self.installList = Gui._GetBundlePackNamesFromList(self.bundlePackList)
        if self.clearConsole.get():
            Gui._ClearConsole()
        try:
            RunWithConfig(
                configPaths=self.configPaths,
                installList=self.installList,
                clean=self.clean.get(),
                build=self.build.get(),
                release=self.release.get(),
                install=self.install.get(),
                uninstall=self.uninstall.get(),
                run=self.run.get(),
                printConfig=self.printConfig.get())
        except Exception:
            print("ERROR CALLSTACK")
            traceback.print_exc()


    def _Clean(self) -> None:
        self.installList = Gui._GetBundlePackNamesFromList(self.bundlePackList)
        if self.clearConsole.get():
            Gui._ClearConsole()
        try:
            RunWithConfig(
                configPaths=self.configPaths,
                installList=self.installList,
                clean=True,
                printConfig=self.printConfig.get())
        except Exception:
            print("ERROR CALLSTACK")
            traceback.print_exc()


    def _Build(self) -> None:
        self.installList = Gui._GetBundlePackNamesFromList(self.bundlePackList)
        if self.clearConsole.get():
            Gui._ClearConsole()
        try:
            RunWithConfig(
                configPaths=self.configPaths,
                installList=self.installList,
                build=True,
                printConfig=self.printConfig.get())
        except Exception:
            print("ERROR CALLSTACK")
            traceback.print_exc()


    def _Release(self) -> None:
        self.installList = Gui._GetBundlePackNamesFromList(self.bundlePackList)
        if self.clearConsole.get():
            Gui._ClearConsole()
        try:
            RunWithConfig(
                configPaths=self.configPaths,
                installList=self.installList,
                release=True,
                printConfig=self.printConfig.get())
        except Exception:
            print("ERROR CALLSTACK")
            traceback.print_exc()


    def _Install(self) -> None:
        self.installList = Gui._GetBundlePackNamesFromList(self.bundlePackList)
        if self.clearConsole.get():
            Gui._ClearConsole()
        try:
            RunWithConfig(
                configPaths=self.configPaths,
                installList=self.installList,
                install=True,
                printConfig=self.printConfig.get())
        except Exception:
            print("ERROR CALLSTACK")
            traceback.print_exc()


    def _Uninstall(self) -> None:
        self.installList = Gui._GetBundlePackNamesFromList(self.bundlePackList)
        if self.clearConsole.get():
            Gui._ClearConsole()
        try:
            RunWithConfig(
                configPaths=self.configPaths,
                installList=self.installList,
                uninstall=True,
                printConfig=self.printConfig.get())
        except Exception:
            print("ERROR CALLSTACK")
            traceback.print_exc()


    def _RunGame(self) -> None:
        self.installList = Gui._GetBundlePackNamesFromList(self.bundlePackList)
        if self.clearConsole.get():
            Gui._ClearConsole()
        try:
            RunWithConfig(
                configPaths=self.configPaths,
                installList=self.installList,
                run=True,
                printConfig=self.printConfig.get())
        except Exception:
            print("ERROR CALLSTACK")
            traceback.print_exc()
