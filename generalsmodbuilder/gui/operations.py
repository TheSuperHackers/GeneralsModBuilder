from dataclasses import dataclass


@dataclass(frozen=True)
class Operation:
    """One build operation, offered by the gui as a sequence entry and as a single action."""

    label: str
    runKwarg: str
    # The change log is made from the json configuration alone. Every other operation also
    # needs the selected bundle packs, the tools, the user runner and the shared engine.
    usesBuildContext: bool = True


OPERATIONS: tuple[Operation, ...] = (
    Operation("Make Change Log", "makeChangeLog", usesBuildContext=False),
    Operation("Clean", "clean"),
    Operation("Build", "build"),
    Operation("Build Release", "release"),
    Operation("Install", "install"),
    Operation("Run Game", "run"),
    Operation("Uninstall", "uninstall"),
)
