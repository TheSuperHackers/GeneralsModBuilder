# This python script is called on build via ModBundlesItems.json configuration

def OnEvent(**kwargs) -> None:
    print("OnBuildItem.py called ...")

    bundleItem = kwargs.get("_bundleItem")
    rawBundleItem = kwargs.get("_rawBundleThing")
    bigBundleItem = kwargs.get("_bigBundleThing")

    assert bundleItem != None, "_bundleItem kwargs not found"
    assert rawBundleItem != None, "_rawBundleThing kwargs not found"
    assert bigBundleItem != None, "_bigBundleItem kwargs not found"
