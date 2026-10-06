#!/usr/bin/env python3
"""Check dependency isolation; this is not an Android runtime acceptance test."""
import pathlib
import plistlib
import subprocess
import sys
import unittest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]

class NoJITTarget(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, str(ROOT / 'scripts/generate_nojit_project.py')], check=True)
        cls.project = yaml.safe_load((ROOT / 'src/app/project-nojit.yml').read_text())
        cls.target = cls.project['targets']['Husk-NoJIT']

    def test_debugger_and_native_runtime_are_absent(self):
        self.assertEqual(set(self.project['targets']), {'Husk-NoJIT'})
        self.assertEqual({s['path'] for s in self.target['sources']}, {'Husk', 'Husk/Resources'})
        excluded = self.target['sources'][0]['excludes']
        for name in ['JIT*.swift', 'TL*.swift', 'TranslationLayer.swift', 'husk-jit.js']:
            self.assertIn(name, excluded)
        dependencies = str(self.target['dependencies'])
        self.assertNotIn('StikJIT', dependencies)
        self.assertNotIn('HuskJITHelper', dependencies)
        self.assertIn('nojit/lib/libqemu', dependencies)
        self.assertIn('libANGLE-shared.dylib', dependencies)
        self.assertNotIn('-lhusk_rppairing', str(self.target))
        self.assertNotIn('postBuildScripts', self.target)

    def test_ordinary_signing_and_no_pairing(self):
        entitlements = plistlib.loads((ROOT / 'src/app/Husk/Husk-NoJIT.entitlements').read_bytes())
        self.assertEqual(entitlements, {
            "com.apple.developer.kernel.increased-memory-limit": True,
            "com.apple.developer.kernel.extended-virtual-addressing": True,
        })
        plist = plistlib.loads((ROOT / 'src/app/Husk/Info-NoJIT.plist').read_bytes())
        self.assertEqual(plist['HuskExecutionMode'], 'TCI')
        for key in ['LSApplicationQueriesSchemes', 'NSBonjourServices', 'BGTaskSchedulerPermittedIdentifiers']:
            self.assertNotIn(key, plist)

    def test_jit_target_is_preserved(self):
        project = yaml.safe_load((ROOT / 'src/app/project.yml').read_text())
        self.assertIn('HuskJITHelper', project['targets'])
        self.assertNotIn('HUSK_NO_JIT', str(project['settings']['base']))

if __name__ == '__main__':
    unittest.main()
