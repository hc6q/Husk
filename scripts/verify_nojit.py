#!/usr/bin/env python3
"""Reject a native backend, JIT objects, or JIT payload in a No-JIT build."""
import argparse
import json
import pathlib
import plistlib
import re
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--build", type=pathlib.Path, required=True)
parser.add_argument("--app", type=pathlib.Path)
args = parser.parse_args()
header = (args.build / "config-host.h").read_text()
assert re.search(r"^#define CONFIG_TCG_INTERPRETER(?: 1)?$", header, re.M), "TCI is not enabled"
assert not re.search(r"^#define CONFIG_TCG_THREADED_INTERPRETER(?: 1)?$", header, re.M)
commands = json.loads((args.build / "compile_commands.json").read_text())
sources = {pathlib.Path(row["file"]).name for row in commands}
assert "tci.c" in sources and "husk-nojit.c" in sources, "TCI/substrate object absent"
assert not sources.intersection({"husk-ios-jit.c", "husk-brk.S"}), "JIT substrate compiled"
for row in commands:
    if pathlib.Path(row["file"]).name in {"region.c", "tcg.c", "husk-nojit.c"}:
        command = row.get("command", " ".join(row.get("arguments", [])))
        assert "-DHUSK_NO_JIT=1" in command, "No-JIT guard missing"

if args.app:
    app = args.app
    # Legal notices are text resources, not executable Stik dependencies.
    stik = list((app / "Frameworks").glob("*Stik*"))
    assert not stik, f"StikJIT framework present: {stik}"
    assert not list(app.glob("**/*JITHelper*")), "debugger helper present"
    assert not list(app.glob("**/husk-jit.js")), "JIT script present"
    plist = plistlib.loads((app / "Info.plist").read_bytes())
    assert plist["HuskExecutionMode"] == "TCI"
    assert not plist.get("LSApplicationQueriesSchemes"), "JIT schemes present"
    assert not plist.get("NSBonjourServices"), "pairing service present"
    qemu = app / "Frameworks/libqemu-aarch64-softmmu.dylib"
    symbols = subprocess.check_output(["nm", "-g", str(qemu)], text=True)
    assert "_husk_tci_enabled" in symbols
    assert "_husk_brk_" not in symbols and "BreakGetJITMapping" not in symbols
    executable = app / plist["CFBundleExecutable"]
    links = subprocess.check_output(["otool", "-L", str(executable)], text=True)
    assert "StikJIT" not in links
    entitlements = plistlib.loads((pathlib.Path(__file__).resolve().parents[1]
                                  / "src/app/Husk/Husk-NoJIT.entitlements").read_bytes())
    allowed = {"com.apple.developer.kernel.increased-memory-limit",
               "com.apple.developer.kernel.extended-virtual-addressing"}
    assert set(entitlements) == allowed and all(v is True for v in entitlements.values()), \
        "No-JIT permits only the original public memory capabilities"
print("[NoJIT] build audit passed (device boot/APK validation is still required)")
