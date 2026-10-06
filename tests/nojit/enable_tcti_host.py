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
print('[NoJIT] Isolated TCTI host experiment configured; allocator remains RW')
