#!/usr/bin/env python3
"""Derive an isolated No-JIT target from the canonical XcodeGen project."""
import copy
import pathlib
import plistlib
import yaml

root = pathlib.Path(__file__).resolve().parents[1]
app = root / "src/app"
project = yaml.safe_load((app / "project.yml").read_text())
project["name"] = "Husk-NoJIT"
project["settings"]["base"].update({
    "HUSK_BUNDLE_IDENTIFIER": "com.husk.nojit",
    "HUSK_ENTITLEMENTS": "Husk/Husk-NoJIT.entitlements",
    "SWIFT_ACTIVE_COMPILATION_CONDITIONS": "$(inherited) HUSK_NO_JIT",
    "GCC_PREPROCESSOR_DEFINITIONS": ["$(inherited)", "HUSK_NO_JIT=1"],
})
target = copy.deepcopy(project["targets"]["Husk"])
project["targets"] = {"Husk-NoJIT": target}
target["sources"] = [source for source in target["sources"]
                     if source["path"] in ("Husk", "Husk/Resources")]
for source in target["sources"]:
    source.setdefault("excludes", []).extend([
        "JIT*.swift", "TranslationLayer.swift", "TL*.swift",
        "HuskGamepad.swift", "VirtualPad.swift", "husk-jit.js",
        "Info*.plist", "*.entitlements",
    ])
settings = target["settings"]["base"]
settings["INFOPLIST_FILE"] = "Husk/Info-NoJIT.plist"
settings["LIBRARY_SEARCH_PATHS"] = ["$(inherited)", "$(SRCROOT)/../../build/ios-arm64/nojit/lib"]
settings["OTHER_LDFLAGS"] = [flag for flag in settings["OTHER_LDFLAGS"]
                            if flag != "-lhusk_rppairing"]
target["dependencies"] = [dep for dep in target["dependencies"]
                          if "target" not in dep and "MoltenVK" not in dep.get("framework", "")]
for dep in target["dependencies"]:
    if "libqemu" in dep["framework"]:
        dep["framework"] = dep["framework"].replace("ios-arm64/lib/", "ios-arm64/nojit/lib/")
# MoltenVK only belongs to the removed native APK Vulkan driver. QEMU's
# existing GPU route is virglrenderer -> ANGLE -> Metal and stays intact.
target.pop("postBuildScripts", None)

plist = plistlib.loads((app / "Husk/Info.plist").read_bytes())
for key in ("BGTaskSchedulerPermittedIdentifiers", "LSApplicationQueriesSchemes",
            "NSBonjourServices", "NSLocalNetworkUsageDescription"):
    plist.pop(key, None)
plist["CFBundleDisplayName"] = "Husk No-JIT"
plist["CFBundleURLTypes"][0]["CFBundleURLSchemes"] = ["husk-nojit"]
plist["HuskExecutionMode"] = "TCI"
(app / "Husk/Info-NoJIT.plist").write_bytes(plistlib.dumps(plist))
(app / "Husk/Husk-NoJIT.entitlements").write_bytes(plistlib.dumps({}))
(app / "project-nojit.yml").write_text(yaml.safe_dump(project, sort_keys=False))
