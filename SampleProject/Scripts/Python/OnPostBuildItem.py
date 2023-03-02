# This python script is called on build via ModBundleItems.json configuration

def OnEvent(**kwargs) -> None:
    print("OnPostBuildItem.py called ...")

    rawBuildThing = kwargs.get("_rawBuildThing")
    bigBuildThing = kwargs.get("_bigBuildThing")

    assert rawBuildThing != None, "_rawBuildThing kwargs not found"
    assert bigBuildThing != None, "_bigBuildThing kwargs not found"
