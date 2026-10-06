#!/usr/bin/env python3
"""Match Darwin's 16 KiB ROM allocation for a Linux snapshot-only test.

The official snapshot contains page-rounded ROM RAMBlocks from macOS. This
does not change guest RAM, TCI, CPU features, memory protection or the iOS build.
"""
from pathlib import Path
import sys

if sys.platform != "linux":
    raise SystemExit("This compatibility patch is only for Linux validation")
file = Path(sys.argv[1]) / "hw/core/loader.c"
old = """                                      rom->datasize, rom->romsize,
                                      fw_cfg_resized,"""
new = """                                      ROUND_UP(rom->datasize, 0x4000),
                                      ROUND_UP(rom->romsize, 0x4000),
                                      fw_cfg_resized,"""
source = file.read_text()
if new not in source:
    if source.count(old) != 1:
        raise SystemExit("Pinned QEMU ROM allocation shape changed")
    file.write_text(source.replace(old, new, 1))
print("[NoJIT] Linux test ROM allocation aligned to Darwin's 16 KiB pages")
