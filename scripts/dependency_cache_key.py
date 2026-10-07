#!/usr/bin/env python3
"""Fingerprint iOS dependencies without invalidating ANGLE for QEMU changes."""
import hashlib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root/'scripts/build_ios.sh').read_text().split('stage_qemu() {',1)[0]
# These flags only affect the QEMU stage, not installed dependency libraries.
start = source.index('HUSK_NO_JIT="')
end = source.index('ARCH=arm64',start)
source = source[:start]+source[end:]
source = source.replace('export HUSK_QEMU_IOS_CROSS=1\n','')
digest = hashlib.sha256(source.encode())
# Installed pkg-config files contain absolute sysroot prefixes. A repository
# rename changes the Actions checkout path; that cache cannot be reused there.
digest.update(b'\0sysroot-prefix\0')
digest.update(str(root / 'build/ios-arm64/sysroot').encode())
for name in (
    'scripts/sources.sh', 'scripts/build_angle_ios.sh', 'scripts/build_gpu_ios.sh',
    'patches/pixman-0.38.0.patch', 'patches/libslirp-v4.9.1.patch',
    'patches/husk-epoxy-ios-egl-path.patch',
):
    digest.update(name.encode())
    digest.update((root/name).read_bytes())
print(f'deps={digest.hexdigest()}')
