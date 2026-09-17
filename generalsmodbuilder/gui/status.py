IDLE = "idle"
RUNNING = "running"
ABORTING = "aborting"


def FormatStatusText(state: str, packCount: int, selectedCount: int, activity: str = "") -> str:
    """The one line of the status bar. An unknown state reads as idle rather than raising."""
    if state == RUNNING:
        return f"Running {activity}" if activity else "Running"
    if state == ABORTING:
        return f"Aborting {activity}" if activity else "Aborting"

    packs = f"{packCount} bundle pack" if packCount == 1 else f"{packCount} bundle packs"
    selected = "none selected" if selectedCount == 0 else f"{selectedCount} selected"
    return f"Idle — {packs}, {selected}"


def StatusStyle(state: str) -> str:
    """The label style that colours the status dot."""
    return "Busy.TLabel" if state in (RUNNING, ABORTING) else "Ok.TLabel"
