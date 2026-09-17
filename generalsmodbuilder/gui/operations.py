from dataclasses import dataclass


@dataclass(frozen=True)
class Operation:
    """One build operation, offered by the gui as a sequence entry and as a single action."""

    label: str
    runKwarg: str
    hint: str
    # The change log is made from the json configuration alone. Every other operation also
    # needs the selected bundle packs, the tools, the user runner and the shared engine.
    usesBuildContext: bool = True


OPERATIONS: tuple[Operation, ...] = (
    Operation("Make Change Log", "makeChangeLog",
              "Generates the change log documents from the change log configuration.",
              usesBuildContext=False),
    Operation("Clean", "clean",
              "Uninstalls, then deletes the build and release folders."),
    Operation("Build", "build",
              "Builds the ticked bundle packs into the build folder."),
    Operation("Build Release", "release",
              "Builds, then packs the release archives into the release folder."),
    Operation("Install", "install",
              "Copies or links the built bundle packs into the game folder."),
    Operation("Run Game", "run",
              "Starts the game with the executable and arguments above."),
    Operation("Uninstall", "uninstall",
              "Removes the installed bundle items and puts back the game files they replaced."),
)
