"""Exercise the real blocking script against controlled Android command failures."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[2]/'src/app/Husk/Resources/nojit-disable-bluetooth.sh'
FAKE='''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
p=Path(os.environ['BT_STATE']); s=json.loads(p.read_text()); a=sys.argv[1:]
tool=Path(sys.argv[0]).name
if tool=='pm':
    if a[0]=='list' and s['disabled']: print('package:com.android.bluetooth')
    elif a[0]=='disable-user':
        s['disable_calls']+=1
        if not s.get('refuse_disable'): s['disabled']=True
elif tool=='am':
    s['stop_calls']+=1
    if not s.get('refuse_stop'): s['running']=False
elif tool=='pidof':
    if s['running']: print('1234')
    else: p.write_text(json.dumps(s)); sys.exit(1)
p.write_text(json.dumps(s))
'''
class BluetoothBlock(unittest.TestCase):
    def run_case(self,**overrides):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); state=root/'state.json'
            state.write_text(json.dumps({'disabled':False,'running':True,'disable_calls':0,'stop_calls':0,**overrides}))
            for name in ('pm','am','pidof','sync'):
                p=root/name;p.write_text(FAKE);p.chmod(0o755)
            result=subprocess.run(['sh',str(SCRIPT)],env=dict(os.environ,PATH=tmp+':'+os.environ['PATH'],BT_STATE=str(state)),capture_output=True,text=True)
            return result,json.loads(state.read_text())
    def test_disable_and_stop_verified(self):
        r,s=self.run_case();self.assertEqual(r.returncode,0,r.stderr)
        self.assertTrue(s['disabled']);self.assertFalse(s['running'])
        self.assertIn('Bluetooth startup blocked',r.stdout)
    def test_disabled_snapshot_process_still_stopped(self):
        r,s=self.run_case(disabled=True);self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(s['disable_calls'],0);self.assertEqual(s['stop_calls'],1)
        self.assertFalse(s['running'])
    def test_false_disable_success_not_accepted(self):
        r,s=self.run_case(refuse_disable=True);self.assertNotEqual(r.returncode,0)
        self.assertEqual(s['stop_calls'],0);self.assertNotIn('Bluetooth startup blocked',r.stdout)
    def test_running_process_not_accepted(self):
        r,s=self.run_case(refuse_stop=True);self.assertEqual(r.returncode,4)
        self.assertTrue(s['running']);self.assertNotIn('Bluetooth startup blocked',r.stdout)
if __name__=='__main__': unittest.main()
