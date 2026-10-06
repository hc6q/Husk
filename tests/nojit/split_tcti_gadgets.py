#!/usr/bin/env python3
"""Bound compiler memory for the pinned static TCTI gadget generator.

Only complete function/lookup-table groups are split. No instruction, lookup,
or runtime allocation changes; never invoked by the published TCI iOS build.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
meson = root/'tcg/meson.build'
text = meson.read_text()
marker = '# HUSK: bounded static TCTI translation units'
if marker in text:
    print('[NoJIT] TCTI static translation units already split')
    raise SystemExit(0)
generator = root/'tcg/aarch64-tcti/tcti-gadget-gen.py'
subprocess.run([sys.executable, str(generator)], cwd=root, check=True)
dest = root/'tcg/husk-tcti-chunks'
dest.mkdir(exist_ok=False)
parts = []
evidence = []
for source in sorted((root/'tcg').glob('tcti_*_gadgets.c')):
    body = source.read_text()
    header = re.search(r'^#include "(tcti_[^"]+\.h)"$', body, re.M)
    assert header, source
    segments = body.split('\n};\n')
    groups = [s+'\n};\n' if i < len(segments)-1 else s
              for i, s in enumerate(segments)]
    assert ''.join(groups) == body, 'Generated C text changed while splitting'
    largest = 0
    for i, group in enumerate(groups):
        if not group.strip():
            continue
        largest = max(largest, len(group.encode()))
        assert largest < 8*1024*1024, 'Pinned group exceeds compiler memory bound'
        name = f'husk_{source.stem}_{i:04d}.c'
        # Keep all static function definitions beside their original table.
        (dest/name).write_text(f'#include "../{header.group(1)}"\n'+group)
        parts.append(f'husk-tcti-chunks/{name}')
    evidence.append(dict(file=source.name, sha256=hashlib.sha256(body.encode()).hexdigest(),
                         groups=len(groups), largest_group_bytes=largest))
    source.unlink()  # Generated originals are not compiled or needed afterwards.
assert parts
pattern = r"if get_option\('tcg_threaded_interpreter'\)\n.*?\nendif\n(?=\ntcg_ss = tcg_ss.apply)"
matches = list(re.finditer(pattern, text, re.S))
assert len(matches) == 1, 'Pinned TCTI Meson source shape changed'
replacement = marker+'\ntcti_gadgets = []\nif get_option(\'tcg_threaded_interpreter\')\n  tcg_ss.add(files(\n'
replacement += ''.join(f"    '{p}',\n" for p in parts)+'  ))\nendif\n'
meson.write_text(text[:matches[0].start()]+replacement+text[matches[0].end():])
(root/'tcg/husk-tcti-split-report.json').write_text(json.dumps(evidence, indent=2)+'\n')
print(f'[NoJIT] Static TCTI source split into {len(parts)} units; C text groups preserved exactly')
