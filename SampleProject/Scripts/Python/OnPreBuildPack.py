# This python script is called on build via ModBundlesPacks.json configuration

def OnEvent(**kwargs) -> None:
    print("OnPreBuildPack.py called ...")

    bundlePack = kwargs.get("_bundlePack")

    assert(bundlePack != None, "_bundlePack kwargs not found")
