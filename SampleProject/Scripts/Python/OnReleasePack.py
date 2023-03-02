# This python script is called on build via ModBundlePacks.json configuration

def OnEvent(**kwargs) -> None:
    print("OnReleasePack.py called ...")

    rawBuildThing = kwargs.get("_rawBuildThing")
    releaseBuildThing = kwargs.get("_releaseBuildThing")

    assert rawBuildThing != None, "_rawBuildThing kwargs not found"
    assert releaseBuildThing != None, "_releaseBuildThing kwargs not found"
