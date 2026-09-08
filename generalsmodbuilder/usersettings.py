import json
import os
import platformdirs
from generalsmodbuilder.data.runner import UserRunner, MakeUserRunnerFromJson
from generalsmodbuilder.util import JsonFile


def GetUserSettingsFile() -> str:
    return os.path.join(
        platformdirs.user_config_dir("GeneralsModBuilder", "TheSuperHackers"), "UserSettings.json")


def LoadUserRunner(path: str) -> UserRunner:
    """
    Reads the game launch settings of this user. A file that cannot be read is reported
    and gives the settings that change nothing, because the gui writes this file and a
    bad hand edit must not lock the user out of it.
    """
    if not os.path.isfile(path):
        return UserRunner()

    try:
        return MakeUserRunnerFromJson(JsonFile(path))
    except Exception as error:
        print(f"User settings {path} are not read: {error}")
        return UserRunner()


def SaveUserRunner(path: str, gameInstallPath: str, gameExeFile: str, gameExeArgs: str) -> None:
    jUserRunner = {
        "version": 1,
        "gameInstallPath": gameInstallPath,
        "gameExeFile": gameExeFile,
        "gameExeArgs": gameExeArgs,
    }

    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump({"userRunner": jUserRunner}, file, indent=4)
