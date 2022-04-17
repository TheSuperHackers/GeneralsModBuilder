# This python script is called on build via ModBundlesPacks.json configuration

def OnEvent(**kwargs) -> None:
    print("OnPreBuildPack.py called ...")

    if False:
        bundlePack = kwargs.get("BundlePack")
        if bundlePack != None:
            print(bundlePack)

        info = kwargs.get("Info")
        if info != None:
            print(info)
