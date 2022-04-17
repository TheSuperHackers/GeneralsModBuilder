# This python script is called on build via ModBundlesItems.json configuration

def OnPreBuild(**kwargs) -> None:
    print("OnPreBuildItem.py called ...")

    if False:
        bundleItem = kwargs.get("BundleItem")
        if bundleItem != None:
            print(bundleItem)

        info = kwargs.get("Info")
        if info != None:
            print(info)
