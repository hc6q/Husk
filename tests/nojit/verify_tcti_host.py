#!/usr/bin/env python3
"""Fail closed if the isolated experiment compiled native/JIT CPU machinery."""
from pathlib import Path
import json,re,subprocess,sys
root=Path(sys.argv[1])
header=(root/'config-host.h').read_text()
assert re.search(r'^#define CONFIG_TCG_THREADED_INTERPRETER(?: 1)?$',header,re.M)
assert not re.search(r'^#define CONFIG_TCG_INTERPRETER(?: 1)?$',header,re.M)
commands=json.loads((root/'compile_commands.json').read_text())
names={Path(c['file']).name for c in commands}
assert 'husk-nojit.c' in names
assert not names.intersection({'husk-ios-jit.c','husk-brk.S','tci.c'})
assert any('tcti_' in n for n in names), 'Static threaded gadgets absent'
for c in commands:
 if Path(c['file']).name in {'region.c','tcg.c','husk-nojit.c'}:
  assert '-DHUSK_NO_JIT=1' in c.get('command',' '.join(c.get('arguments',[])))
symbols=subprocess.check_output(['nm','-g',str(root/'qemu-system-aarch64')],text=True)
assert 'BreakGetJITMapping' not in symbols and 'husk_brk_' not in symbols
print('[NoJIT] TCTI static-gadget build audit passed; runtime still requires guard and APK acceptance')
