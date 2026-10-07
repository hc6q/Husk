"""Exercise profile apply/restore and failure recovery against fake Android tools."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2]/'src/app/Husk/Resources/nojit-performance.sh'
TOOLS = '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
p=Path(os.environ['FAKE_ANDROID_STATE']); s=json.loads(p.read_text())
a=sys.argv[1:]; tool=Path(sys.argv[0]).name
if tool=='settings':
    key=a[1]+':'+a[2]
    if a[0]=='get': print(s['settings'].get(key,'null'))
    elif a[0]=='put': s['settings'][key]=a[3]
    elif a[0]=='delete': s['settings'].pop(key,None)
else:
    key=a[0]
    if len(a)==1:
        print('Physical '+key+': '+s['physical'][key])
        if key in s['override']: print('Override '+key+': '+s['override'][key])
    elif key=='density' and os.environ.get('FAIL_DENSITY')=='1': sys.exit(7)
    elif a[1]=='reset': s['override'].pop(key,None)
    else: s['override'][key]=a[1]
p.write_text(json.dumps(s))
'''

class PerformanceProfile(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.initial={'settings':{'global:window_animation_scale':'0.5','system:show_touches':'1'},'physical':{'size':'360x800','density':'240'},'override':{'size':'400x900','density':'300'}}
        self.db=self.root/'state.json'; self.db.write_text(json.dumps(self.initial))
        for name in ('settings','wm'):
            tool=self.root/name; tool.write_text(TOOLS); tool.chmod(0o755)
        self.script=self.root/'profile.sh'
        self.script.write_text(SCRIPT.read_text().replace('/data/local/tmp/rottweiler-performance-v1',str(self.root/'backup')))
        self.env=dict(os.environ,PATH=str(self.root)+':'+os.environ['PATH'],FAKE_ANDROID_STATE=str(self.db))
    def run_profile(self,mode,env=None):
        return subprocess.run(['sh',str(self.script),mode],env=env or self.env,capture_output=True,text=True)
    def test_apply_idempotent_and_restore_custom_values(self):
        result=self.run_profile('apply'); self.assertEqual(result.returncode,0,result.stderr)
        state=json.loads(self.db.read_text())
        self.assertEqual(state['override'],{'size':'270x600','density':'180'})
        self.assertTrue(all(v=='0' for v in state['settings'].values()))
        original_backup=(self.root/'backup/window_animation_scale').read_text()
        self.assertEqual(self.run_profile('apply').returncode,0)
        self.assertEqual((self.root/'backup/window_animation_scale').read_text(),original_backup)
        self.assertEqual(self.run_profile('restore').returncode,0)
        self.assertEqual(json.loads(self.db.read_text()),self.initial)
    def test_partial_failure_preserves_backup_for_restore(self):
        result=self.run_profile('apply',dict(self.env,FAIL_DENSITY='1'))
        self.assertNotEqual(result.returncode,0)
        self.assertFalse((self.root/'backup/applied').exists())
        self.assertEqual(self.run_profile('restore').returncode,0)
        self.assertEqual(json.loads(self.db.read_text()),self.initial)
    def test_restore_without_profile_does_nothing(self):
        self.assertEqual(self.run_profile('restore').returncode,0)
        self.assertEqual(json.loads(self.db.read_text()),self.initial)

if __name__=='__main__': unittest.main()
