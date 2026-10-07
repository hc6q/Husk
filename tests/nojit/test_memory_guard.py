#!/usr/bin/env python3
"""Prove that the Linux smoke test's executable-memory guard actually blocks."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

@unittest.skipUnless(sys.platform.startswith('linux'), 'LD_PRELOAD guard is Linux-only')
class MemoryGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='husk-memory-guard-')
        directory = Path(cls.temp.name)
        cls.guard = directory/'guard.so'
        cls.probe = directory/'probe'
        subprocess.run(['cc','-shared','-fPIC',str(ROOT/'tests/nojit/mmap_guard.c'),
                        '-ldl','-o',str(cls.guard)],check=True)
        source = directory/'probe.c'
        source.write_text('''#include <sys/mman.h>
#include <stdlib.h>
int main(int argc, char **argv) {
    int mode = atoi(argv[1]);
    int prot = PROT_READ | PROT_WRITE;
    if (mode == 1) prot |= PROT_EXEC;
    if (mode == 2) prot = PROT_READ | PROT_EXEC;
    void *p = mmap(0,4096,prot,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if (p == MAP_FAILED) return 2;
    if (mode == 3) return mprotect(p,4096,PROT_READ|PROT_EXEC);
    *(volatile char *)p = 42;
    return munmap(p,4096);
}
''')
        subprocess.run(['cc',str(source),'-o',str(cls.probe)],check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_rw_is_allowed(self):
        result = subprocess.run([str(self.probe),'0'],
                                env=dict(os.environ,LD_PRELOAD=str(self.guard)))
        self.assertEqual(result.returncode,0)

    def test_dynamic_execution_is_rejected(self):
        for mode in ('1','2','3'):
            with self.subTest(mode=mode):
                result = subprocess.run([str(self.probe),mode],capture_output=True,
                                        env=dict(os.environ,LD_PRELOAD=str(self.guard)))
                self.assertEqual(result.returncode,90)
                self.assertIn(b'executable dynamic mapping requested',result.stderr)

if __name__ == '__main__':
    unittest.main()
