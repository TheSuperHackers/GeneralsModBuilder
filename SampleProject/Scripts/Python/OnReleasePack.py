# This python script is called on build via ModBundlesPacks.json configuration

def OnEvent(**kwargs) -> None:
    print("OnReleasePack.py called ...")

    rawBundleItem = kwargs.get("_rawBundleThing")
    bigBundleItem = kwargs.get("_releaseBundleThing")
    bigBundleItem = kwargs.get("_installBundleThing")

    assert rawBundleItem != None, "_rawBundleThing kwargs not found"
    assert bigBundleItem != None, "_releaseBundleThing kwargs not found"
    assert bigBundleItem != None, "_installBundleThing kwargs not found"
