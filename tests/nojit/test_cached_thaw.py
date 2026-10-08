"""Exercise the shipped script against Android command state transitions."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2]/'src/app/Husk/Resources/nojit-thaw-cached.sh'
FAKE = '''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
p=Path(os.environ['THAW_STATE']); s=json.loads(p.read_text()); a=sys.argv[1:]
tool=Path(sys.argv[0]).name
if tool=='mktemp': print(str(p.parent/'dump'))
elif tool=='settings':
    if a[0]=='put': s['writes']+=1; s['disabled']=True
    else: print('disabled' if s['disabled'] else 'enabled')
elif tool=='dumpsys':
    if s.get('partial'): print('DUMP TIMEOUT'); sys.exit(0)
    print('Freezer settings\\n  use_freezer=false')
    print('  Apps frozen: '+str(len(s['pids'])))
    for pid in s['pids']: print('    1234: '+str(pid)+' org.test.cached')
elif tool=='am':
    assert a[:2]==['unfreeze','--sticky']
    s['calls'].append(a[2])
    if not s.get('refuse'): s['pids'].remove(int(a[2]))
p.write_text(json.dumps(s))
'''

class CachedThaw(unittest.TestCase):
    def run_case(self, **overrides):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); state=root/'state.json'
            state.write_text(json.dumps({'disabled':False, 'writes':0, 'calls':[], 'pids':[123,456], **overrides}))
            for name in ('settings','dumpsys','am','mktemp','sync','sleep'):
                p=root/name; p.write_text(FAKE); p.chmod(0o755)
            r=subprocess.run(['sh',str(SCRIPT)],capture_output=True,text=True,timeout=20,
                env=dict(os.environ,PATH=tmp+':'+os.environ['PATH'],THAW_STATE=str(state)))
            return r,json.loads(state.read_text())

    def test_restored_processes_thawed_once(self):
        r,s=self.run_case(); self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(s['calls'],['123','456']); self.assertEqual(s['writes'],1)
        self.assertEqual(s['pids'],[]); self.assertIn('Apps frozen: 0',r.stdout)

    def test_empty_snapshot(self):
        r,s=self.run_case(pids=[]); self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(s['calls'],[])

    def test_false_success_does_not_certify(self):
        r,s=self.run_case(refuse=True); self.assertNotEqual(r.returncode,0)
        self.assertEqual(s['calls'],['123','456']); self.assertNotIn('Apps frozen: 0',r.stdout)

    def test_partial_dump_never_executes_pids(self):
        r,s=self.run_case(partial=True); self.assertNotEqual(r.returncode,0)
        self.assertEqual(s['calls'],[])

    def test_invalid_pid_rejected(self):
        r,s=self.run_case(pids=['123;touch injected']); self.assertNotEqual(r.returncode,0)
        self.assertEqual(s['calls'],[])

if __name__=='__main__': unittest.main()
