# This python script is called on build via ModBundlesItems.json configuration

def OnPreBuild(**kwargs) -> None:
    print("OnPreBuildItem.py called ...")

    bundleItem = kwargs.get("_bundleItem")
    info = kwargs.get("info")

    assert(bundleItem != None, "_bundleItem kwargs not found")
    assert(info != None, "info kwargs not found")
