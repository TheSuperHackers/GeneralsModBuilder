# This python script is called on build via ModBundlesPacks.json configuration

def OnEvent(**kwargs) -> None:
    print("OnRunPack.py called ...")

    rawBuildThing = kwargs.get("_rawBuildThing")
    releaseBuildThing = kwargs.get("_releaseBuildThing")
    installBuildThing = kwargs.get("_installBuildThing")

    assert rawBuildThing != None, "_rawBuildThing kwargs not found"
    assert releaseBuildThing != None, "_releaseBuildThing kwargs not found"
    assert installBuildThing != None, "_installBuildThing kwargs not found"
