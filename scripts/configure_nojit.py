#!/usr/bin/env python3
"""Harden the pinned QEMU tree for TCI. Fail if expected source shapes change."""
import pathlib
import sys

qemu = pathlib.Path(sys.argv[1])

def replace(path, old, new):
    file = qemu / path
    source = file.read_text()
    if new in source:
        return
    if old not in source:
        raise SystemExit(f"{path}: unsupported QEMU source shape")
    file.write_text(source.replace(old, new, 1))

# ARM64 macOS can execute ARM64 macOS binaries, but not iOS binaries. Meson
# cannot infer this from configure's generic Darwin machine description.
replace("configure", '  echo "[properties]" >> $cross\n',
        '''  echo "[properties]" >> $cross
  if test "${HUSK_QEMU_IOS_CROSS:-0}" = 1; then
    echo "needs_exe_wrapper = true" >> $cross
  fi
''')

# Never compile the breakpoint allocator or its traps into a No-JIT dylib.
replace("tcg/meson.build", "  'husk-ios-jit.c',\n  'husk-brk.S',\n",
        "  # HUSK_NO_JIT selects one substrate at configure time.\n")
replace("tcg/meson.build", "tcg_ss.add(files(\n",
        """if get_option('tcg_interpreter')
  tcg_ss.add(files('husk-nojit.c'))
else
  tcg_ss.add(files('husk-ios-jit.c', 'husk-brk.S'))
endif

tcg_ss.add(files(
""")

# The original iOS helper sits outside upstream's interpreter guard.
replace("tcg/region.c", "#if defined(__APPLE__) && TARGET_OS_IPHONE\n/*",
        "#if defined(__APPLE__) && TARGET_OS_IPHONE && !defined(CONFIG_TCG_INTERPRETER)\n/*")
replace("tcg/region.c", "    int prot, flags;\n\n",
        """    int prot, flags;

#ifdef HUSK_NO_JIT
#ifndef CONFIG_TCG_INTERPRETER
#error "HUSK_NO_JIT cannot use a native TCG backend"
#endif
    /* TCI emits bytecode as data. No split mapping, MAP_JIT or PROT_EXEC. */
    fprintf(stderr, "[NoJIT] TCI bytecode buffer RW, size=%zu\\n", size);
    return alloc_code_gen_buffer_anon(size, PROT_READ | PROT_WRITE,
                                     MAP_PRIVATE | MAP_ANONYMOUS, errp);
#endif

""")

# Upstream/UTM still invokes these helpers from shared CPU paths with TCI.
# Exclude the APRR implementation entirely when interpreting.
replace("include/tcg/tcg-apple-jit.h",
        "#if defined(__aarch64__) && defined(CONFIG_DARWIN)",
        "#if defined(__aarch64__) && defined(CONFIG_DARWIN) && !defined(CONFIG_TCG_INTERPRETER)")

# Export a backend query in both variants so a mismatched dylib fails closed.
replace("tcg/husk-ios-jit.c", '#include "husk-ios-jit.h"',
        '#include "husk-ios-jit.h"\nHUSK_EXPORT bool husk_tci_enabled(void) { return false; }')
replace("system/qemu.symbols", "  husk_ios_available_memory;",
        "  husk_ios_available_memory;\n  husk_tci_enabled;")
replace("tcg/husk-ios-jit.c", "HUSK_EXPORT bool husk_tci_enabled(void) { return false; }",
        "HUSK_EXPORT bool husk_tci_enabled(void) { return false; }\n"
        "HUSK_EXPORT bool husk_nojit_memory_is_safe(void) { return false; }")
replace("system/qemu.symbols", "  husk_tci_enabled;",
        "  husk_tci_enabled;\n  husk_nojit_memory_is_safe;")
