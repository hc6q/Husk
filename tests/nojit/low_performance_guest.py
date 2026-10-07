#!/usr/bin/env python3
"""Enable LineageOS's existing low-performance boot option in a QCOW2 overlay.

The pinned image already implements android_low_perf in GRUB and its vendor
init script. Only the existing grubenv value 0 -> 1 changes, without changing
its length, FAT allocation, system image, authentication, or SELinux settings.
This cannot change properties cached in an already running snapshot: reboot
and verify ro.boot.low_perf=1 and ro.hw_timeout_multiplier=50 inside Android.
"""
import argparse
import hashlib
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib

BASE_SHA256 = 'a8dbaecc8fdcd682991b078d6bbb7df6972e459208634fa8dcbad24f17208d6a'


def grubenv_value_offset(data):
    """Locate the allocated grubenv file through the pinned FAT32 directory."""
    bps = struct.unpack_from('<H', data, 11)[0]
    spc = data[13]
    reserved = struct.unpack_from('<H', data, 14)[0]
    fats = data[16]
    fat_size = struct.unpack_from('<I', data, 36)[0]
    root = struct.unpack_from('<I', data, 44)[0]
    assert bps == 512 and spc and data[510:512] == b'\x55\xaa'
    cluster_size = bps * spc
    fat_start = reserved * bps
    data_start = (reserved + fats * fat_size) * bps

    def cluster_offset(cluster):
        assert 2 <= cluster < (len(data) - data_start) // cluster_size + 2
        return data_start + (cluster - 2) * cluster_size

    def chain(cluster):
        seen = set()
        while cluster < 0x0ffffff8:
            assert cluster not in seen and cluster >= 2, 'Invalid FAT chain'
            seen.add(cluster)
            yield cluster
            cluster = struct.unpack_from('<I', data, fat_start + cluster * 4)[0] & 0x0fffffff

    matches = []
    for cluster in chain(root):
        start = cluster_offset(cluster)
        for pos in range(start, start + cluster_size, 32):
            entry = data[pos:pos+32]
            if entry[0] in (0, 0xe5) or entry[11] == 0x0f:
                continue
            if entry[:11] == b'GRUBENV    ':
                assert not entry[11] & 0x18, 'grubenv must be a regular file'
                first = (struct.unpack_from('<H', entry, 20)[0] << 16) | struct.unpack_from('<H', entry, 26)[0]
                size = struct.unpack_from('<I', entry, 28)[0]
                assert size == 1024, 'Unexpected grubenv size'
                clusters = list(chain(first))
                assert len(clusters) * cluster_size >= size
                offsets = [cluster_offset(c) + i for c in clusters for i in range(cluster_size)][:size]
                payload = bytes(data[i] for i in offsets)
                assert payload.startswith(b'# GRUB Environment Block\n')
                key = b'\nandroid_low_perf=0\n'
                assert payload.count(key) == 1, 'Expected a single disabled low-performance option'
                matches.append(offsets[payload.index(key) + len(key) - 2])
    assert len(matches) == 1, 'Expected exactly one allocated grubenv'
    return matches[0]


def prepare(base, overlay, qemu_img, qemu_io):
    assert not overlay.exists(), 'Refuse to overwrite any existing disk'
    assert base.resolve() != overlay.resolve()
    with base.open('rb') as file:
        digest = hashlib.file_digest(file, 'sha256').hexdigest()
    assert digest == BASE_SHA256, 'Only the pinned original v12 image is supported'
    with tempfile.TemporaryDirectory(prefix='rottweiler-low-perf-') as folder:
        folder = Path(folder)

        def read_range(start_sector, sectors, target):
            assert start_sector % 8 == 0 and sectors % 8 == 0
            # qemu-img dd count is the input endpoint, including skip.
            subprocess.run([str(qemu_img), 'dd', '--image-opts',
                f'if=driver=qcow2,file.driver=file,file.filename={base.resolve()},force-share=on',
                f'of={target}', 'bs=4096', f'skip={start_sector//8}',
                f'count={(start_sector+sectors)//8}'], check=True)
            assert target.stat().st_size == sectors * 512

        gpt = folder / 'gpt.bin'
        read_range(0, 128, gpt)
        raw = gpt.read_bytes()
        header = bytearray(raw[512:604])
        assert header[:8] == b'EFI PART' and struct.unpack_from('<I', header, 12)[0] == 92
        expected_crc = struct.unpack_from('<I', header, 16)[0]
        header[16:20] = b'\0' * 4
        assert zlib.crc32(header) == expected_crc
        table_sector, count, size, crc = struct.unpack_from('<QIII', raw, 512+72)
        table = raw[table_sector*512:table_sector*512+count*size]
        assert len(table) == count*size and zlib.crc32(table) == crc
        persist = []
        for i in range(count):
            entry = table[i*size:(i+1)*size]
            name = entry[56:128].decode('utf-16-le').rstrip('\0')
            if name == 'persist':
                first, last = struct.unpack_from('<QQ', entry, 32)
                persist.append((first, last-first+1))
        assert len(persist) == 1 and persist[0][1] == 32768
        first, sectors = persist[0]
        image = folder / 'persist.img'
        read_range(first, sectors, image)
        data = image.read_bytes()
        offset = grubenv_value_offset(data)
        assert data[offset] == ord('0')
        sector = offset // 512
        block = bytearray(data[sector*512:(sector+1)*512])
        block[offset % 512] = ord('1')
        source = folder / 'sector.bin'
        source.write_bytes(block)
        overlay.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(qemu_img), 'create', '-f', 'qcow2', '-F', 'qcow2',
                        '-b', str(base.resolve()), str(overlay)], check=True)
        absolute = (first + sector) * 512
        assert ',' not in str(source) and ' ' not in str(source)
        subprocess.run([str(qemu_io), '-f', 'qcow2', '-c',
                        f'write -s {source} {absolute} 512', str(overlay)], check=True)
        subprocess.run([str(qemu_io), '-f', 'qcow2', '-c',
                        f'read -P 49 {absolute + offset % 512} 1', str(overlay)], check=True)
        return {'base_sha256': digest, 'boot_option': 'android_low_perf=1',
                'changed_disk_byte_offset': absolute + offset % 512}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, required=True)
    p.add_argument('--overlay', type=Path, required=True)
    p.add_argument('--qemu-img', type=Path, required=True)
    p.add_argument('--qemu-io', type=Path, required=True)
    a = p.parse_args()
    print(prepare(a.base, a.overlay, a.qemu_img, a.qemu_io))
