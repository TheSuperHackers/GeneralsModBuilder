from conftest import WidgetsOfClass

from generalsmodbuilder.data.runner import UserRunner
from generalsmodbuilder.gui.operations import OPERATIONS


def test_the_window_holds_one_widget_per_offered_choice(MakeGuiWindow):
    gui, holder = MakeGuiWindow()

    assert len(gui.actionButtons) == len(OPERATIONS)
    assert len(WidgetsOfClass(holder, "TCheckbutton")) == len(OPERATIONS) + 4
    assert len(WidgetsOfClass(holder, "TEntry")) == 3
    assert len(WidgetsOfClass(holder, "Treeview")) == 1


def test_the_sequence_boxes_start_where_the_command_line_left_them(MakeGuiWindow):
    initialSequence = {op.runKwarg: False for op in OPERATIONS}
    initialSequence["build"] = True

    gui, _ = MakeGuiWindow(initialSequence)

    assert gui.sequenceVars.keys() == initialSequence.keys()
    assert gui.sequenceVars["build"].get()
    assert not any(var.get() for kwarg, var in gui.sequenceVars.items() if kwarg != "build")


def test_the_game_launch_settings_start_from_the_user_settings(MakeGuiWindow):
    settings = UserRunner(
        absGameInstallDir="C:/Games/Generals",
        relGameExeFile="generals.exe",
        gameExeArgs=["-win", "-quickstart"])

    gui, _ = MakeGuiWindow(settings=settings)

    assert gui.gameInstallPath.get() == "C:/Games/Generals"
    assert gui.gameExeFile.get() == "generals.exe"
    assert gui.gameExeArgs.get() == "-win -quickstart"
