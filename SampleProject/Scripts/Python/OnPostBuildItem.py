# This python script is called on build via ModBundlesItems.json configuration

def OnEvent(**kwargs) -> None:
    print("OnPostBuildItem.py called ...")

    rawBundleItem = kwargs.get("_rawBundleThing")
    bigBundleItem = kwargs.get("_bigBundleThing")

    assert(rawBundleItem != None, "_rawBundleThing kwargs not found")
    assert(bigBundleItem != None, "_bigBundleItem kwargs not found")
