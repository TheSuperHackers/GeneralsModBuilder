# This python script is called on build via ModBundleItems.json configuration

def OnEvent(**kwargs) -> None:
    print("OnBuildItem.py called ...")

    bundleItem = kwargs.get("_bundleItem")
    rawBuildThing = kwargs.get("_rawBuildThing")
    bigBuildThing = kwargs.get("_bigBuildThing")

    assert bundleItem != None, "_bundleItem kwargs not found"
    assert rawBuildThing != None, "_rawBuildThing kwargs not found"
    assert bigBuildThing != None, "_bigBuildThing kwargs not found"
