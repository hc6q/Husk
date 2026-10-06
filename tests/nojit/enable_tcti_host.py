#!/usr/bin/env python3
"""Isolated AArch64 threaded interpreter experiment after Husk integration.

Never invoked by build_ios.sh. TCI remains the published IPA backend.
"""
from pathlib import Path
import sys
root = Path(sys.argv[1])
def change(path, old, new):
    p = root/path
    s = p.read_text()
    if new in s:
        return
    if s.count(old) != 1:
        raise SystemExit(f'Pinned source shape changed: {path}')
    p.write_text(s.replace(old,new,1))
change('tcg/meson.build', "if get_option('tcg_interpreter')\n  tcg_ss.add(files('husk-nojit.c'))", "if get_option('tcg_interpreter') or get_option('tcg_threaded_interpreter')\n  tcg_ss.add(files('husk-nojit.c'))")
change('tcg/husk-nojit.c', '#if !defined(HUSK_NO_JIT) || !defined(CONFIG_TCG_INTERPRETER)', '#if !defined(HUSK_NO_JIT) || (!defined(CONFIG_TCG_INTERPRETER) && !defined(CONFIG_TCG_THREADED_INTERPRETER))')
change('tcg/husk-nojit.c', 'HUSK_EXPORT bool husk_tci_enabled(void) { return true; }', '''HUSK_EXPORT bool husk_tci_enabled(void)
{
#ifdef CONFIG_TCG_INTERPRETER
    return true;
#else
    return false;
#endif
}''')
change('tcg/region.c', '#ifndef CONFIG_TCG_INTERPRETER\n#error "HUSK_NO_JIT cannot use a native TCG backend"', '#if !defined(CONFIG_TCG_INTERPRETER) && !defined(CONFIG_TCG_THREADED_INTERPRETER)\n#error "HUSK_NO_JIT cannot use a native TCG backend"')
change('tcg/region.c', 'fprintf(stderr, "[NoJIT] TCI bytecode buffer RW, size=%zu\\n", size);', '''#ifdef CONFIG_TCG_THREADED_INTERPRETER
    fprintf(stderr, "[NoJIT] TCTI bytecode buffer RW, size=%zu\\n", size);
#else
    fprintf(stderr, "[NoJIT] TCI bytecode buffer RW, size=%zu\\n", size);
#endif''')
change('tcg/region.c', '#if defined(__APPLE__) && TARGET_OS_IPHONE && !defined(CONFIG_TCG_INTERPRETER)', '#if defined(__APPLE__) && TARGET_OS_IPHONE && !defined(CONFIG_TCG_INTERPRETER) && !defined(CONFIG_TCG_THREADED_INTERPRETER)')
change('include/tcg/tcg-apple-jit.h', '#if defined(__aarch64__) && defined(CONFIG_DARWIN) && !defined(CONFIG_TCG_INTERPRETER)', '#if defined(__aarch64__) && defined(CONFIG_DARWIN) && !defined(CONFIG_TCG_INTERPRETER) && !defined(CONFIG_TCG_THREADED_INTERPRETER)')
# Gadgets use x24 and BLR overwrites LR. C helper calls also clobber the
# caller-saved GPRs/SIMD registers. Describe these to the host compiler so it
# saves the ABI state and cannot keep an asm memory operand in a destroyed GPR.
change('tcg/aarch64-tcti/tcg-target.c.inc', '"x25", "x26", "x27", "x28", "cc", "memory"', '''"x16", "x17",
#ifndef __APPLE__
        "x18",
#endif
        "x24", "x25", "x26", "x27", "x28", "x30",
        "v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7",
        "v8", "v9", "v10", "v11", "v12", "v13", "v14", "v15",
        "v16", "v17", "v18", "v19", "v20", "v21", "v22", "v23",
        "v24", "v25", "v26", "v27", "v28", "v29", "v30", "v31",
        "cc", "memory"''')
print('[NoJIT] Isolated TCTI host experiment configured; allocator remains RW')
