#!/usr/bin/env python3
"""Real Android/APK smoke test against the pinned Linux TCI build.

This validates the interpreter and guest, not iOS signing or Metal. Supply the
same vda image/firmware as Husk and disposable writable vars/userdata disks.
The mmap guard must be loaded into QEMU throughout this test.
"""
import argparse
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time
import xml.etree.ElementTree as ET
import wave

p = argparse.ArgumentParser()
p.add_argument('--qemu', type=Path, required=True)
p.add_argument('--guest', type=Path, required=True)
p.add_argument('--apk', type=Path, required=True)
p.add_argument('--guard', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--timeout', type=int, default=7200)
p.add_argument('--memory', type=int, default=2048)
p.add_argument('--snapshot', help='Restore the original userdata snapshot through QMP')
p.add_argument('--file-ram', action='store_true')
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
report = {'platform': 'Linux x86_64 host / Android ARM64 guest', 'backend': 'TCI',
          'boot_completed': False, 'apk_installed': False, 'apk_resumed': False,
          'usb_touch_confirmed': False, 'guest_audio_confirmed': False,
          'ios_device_tested': False}
started = time.monotonic()
def log(message):
    line = f'[{time.monotonic()-started:.1f}s] {message}'
    print(line, flush=True)
    with (a.output/'smoke.log').open('a') as f:
        f.write(line+'\n')

qemu = a.qemu.resolve()
guest = a.guest.resolve()
machine = 'virt,highmem=on,memory-backend=huskram' if a.file_ram else 'virt,highmem=on'
args = [str(qemu), '-M', machine, '-cpu',
        'max,pauth-impdef=on,sve=off,sme=off', '-smp', '4', '-m', str(a.memory),
        '-accel', 'tcg,tb-size=128,thread=single,split-wx=off',
        '-device', 'virtio-balloon-pci,id=huskballoon',
        '-drive', f'if=pflash,unit=0,format=raw,readonly=on,file={guest}/firmware.fd',
        '-drive', f'if=pflash,unit=1,format=qcow2,file={guest}/vars.qcow2',
        '-drive', f'file={guest}/vda.qcow2,if=none,id=vda,format=qcow2,discard=unmap',
        '-drive', f'file={guest}/userdata.qcow2,if=none,id=vdb,node-name=huskvmstate,format=qcow2,discard=unmap',
        '-device', 'virtio-blk-pci,drive=vda,bootindex=0',
        '-device', 'virtio-blk-pci,drive=vdb,bootindex=1',
        '-netdev', 'user,id=net0,hostfwd=tcp:127.0.0.1:15599-:5599',
        '-device', 'virtio-net-pci,netdev=net0',
        '-device', 'virtio-gpu-pci,xres=360,yres=800',
        '-device', 'qemu-xhci,id=usb-bus', '-device', 'usb-tablet,bus=usb-bus.0',
        '-device', 'usb-kbd,bus=usb-bus.0', '-device', 'virtio-rng-pci',
        '-audiodev', f'wav,id=audio,path={a.output.resolve()}/audio.wav',
        '-device', 'virtio-sound-pci,audiodev=audio',
        '-serial', f'file:{a.output.resolve()}/serial.log', '-display', 'none',
        '-qmp', 'tcp:127.0.0.1:15598,server=on,wait=off', '-monitor', 'none']
if a.file_ram:
    args += ['-object', f'memory-backend-file,id=huskram,size={a.memory}M,mem-path={guest}/ram.bin,share=on,prealloc=off']
if a.snapshot:
    args += ['-S']
    # The shipped snapshot has no virtio-sound device; preserve its topology.
    index = args.index('-audiodev')
    del args[index:index+4]
env = dict(os.environ, LD_PRELOAD=str(a.guard.resolve()))
stderr = (a.output/'qemu.log').open('w')
proc = subprocess.Popen(args, stdout=stderr, stderr=stderr, env=env)
bridge = None
sequence = 0
def audit_maps(stage):
    mappings = Path(f'/proc/{proc.pid}/maps').read_text()
    (a.output/f'maps-{stage}.txt').write_text(mappings)
    for line in mappings.splitlines():
        fields = line.split()
        assert not ('w' in fields[1] and 'x' in fields[1]), line
        if 'x' in fields[1]:
            assert len(fields) >= 6 and 'memfd:' not in line, line
    log('[NoJIT] host mappings audited: no W+X or anonymous executable region')

def exchange(command, timeout=300, payload=None):
    global sequence
    sequence += 1
    token = f'__HUSK_EOF__{sequence}:'
    bridge.settimeout(timeout)
    bridge.sendall(f'{command} 2>&1; echo {token}$?\n'.encode())
    if payload is not None:
        bridge.sendall(payload)
    output = b''
    until = time.monotonic()+timeout
    while time.monotonic() < until:
        chunk = bridge.recv(65536)
        if not chunk:
            raise RuntimeError('guest bridge disconnected')
        output += chunk
        if token.encode() in output:
            body, status = output.rsplit(token.encode(), 1)
            if b'\n' in status:
                code = int(status.splitlines()[0].strip())
                log(f'$ {command}\n{body.decode(errors="replace").strip()}\nexit={code}')
                if code:
                    raise RuntimeError(f'guest command failed: {command}')
                return body.decode(errors='replace')
    raise TimeoutError(command)

try:
    log('[NoJIT] Starting Android under mmap/mprotect guard')
    if a.snapshot:
        until = time.monotonic()+120
        while True:
            try:
                control = socket.create_connection(('127.0.0.1',15598),timeout=5)
                break
            except OSError:
                if proc.poll() is not None or time.monotonic() >= until:
                    raise RuntimeError('QMP did not become ready for snapshot restore')
                time.sleep(1)
        with control:
            stream = control.makefile('rwb',buffering=0)
            stream.readline()
            def qmp_command(name, arguments=None):
                stream.write((json.dumps({'execute':name, **({'arguments':arguments} if arguments else {})})+'\n').encode())
                while True:
                    response = json.loads(stream.readline())
                    if 'error' in response:
                        raise RuntimeError(response)
                    if 'return' in response:
                        return response['return']
            qmp_command('qmp_capabilities')
            qmp_command('snapshot-load', {'job-id':'husk-load', 'tag':a.snapshot,
                'vmstate':'huskvmstate', 'devices':['huskvmstate']})
            until = time.monotonic()+600
            while time.monotonic() < until:
                jobs = qmp_command('query-jobs')
                job = next((j for j in jobs if j['id']=='husk-load'),None)
                if job is None:
                    break
                if job.get('error'):
                    raise RuntimeError(job['error'])
                if job['status'] == 'concluded':
                    qmp_command('job-dismiss', {'id':'husk-load'})
                    break
                time.sleep(1)
            else:
                raise TimeoutError('snapshot restore did not finish')
            qmp_command('cont')
            report['snapshot_requested'] = a.snapshot
            log('[NoJIT] Snapshot load job completed; checking Android readiness')
    deadline = started+a.timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f'QEMU exited {proc.returncode}: inspect qemu.log')
        if bridge is None:
            try:
                candidate = socket.create_connection(('127.0.0.1',15599),timeout=3)
                candidate.settimeout(5)
                # Keep a connection only after the guest listener replies.
                candidate.sendall(b'echo HUSK_BRIDGE_READY\n')
                if b'HUSK_BRIDGE_READY' in candidate.recv(4096):
                    bridge = candidate
                else:
                    candidate.close()
            except (OSError, TimeoutError):
                if 'candidate' in locals():
                    candidate.close()
        if bridge is not None:
            if exchange('getprop sys.boot_completed',timeout=60).strip() == '1':
                report['boot_completed'] = True
                report['boot_seconds'] = round(time.monotonic()-started,1)
                log('[NoJIT] Android boot completed')
                audit_maps('boot')
                break
        time.sleep(5)
    else:
        raise TimeoutError('Android did not complete boot')
    payload = a.apk.read_bytes()
    log('[NoJIT] Installing APK')
    remote = '/data/local/tmp/NoJITSmoke.apk'
    exchange(f'head -c {len(payload)} > {remote}',payload=payload)
    assert int(exchange(f'wc -c < {remote}').strip()) == len(payload)
    assert 'Success' in exchange(f'pm install -r -t {remote}',timeout=900)
    report['apk_installed'] = True
    exchange('settings put global device_provisioned 1; settings put secure user_setup_complete 1')
    exchange('input keyevent 82')
    log('[NoJIT] Launching package')
    exchange('monkey -p org.husk.nojitsmoke -c android.intent.category.LAUNCHER 1')
    for _ in range(20):
        activity = exchange('dumpsys activity activities | grep -E "mResumedActivity|topResumedActivity"',timeout=180)
        if 'org.husk.nojitsmoke' in activity:
            report['apk_resumed'] = True
            break
        time.sleep(5)
    assert report['apk_resumed'], 'APK was installed but did not resume'
    audit_maps('apk')
    exchange('uiautomator dump /data/local/tmp/window.xml',timeout=300)
    report['ui_xml'] = exchange('cat /data/local/tmp/window.xml')
    with socket.create_connection(('127.0.0.1',15598),timeout=30) as qmp:
        f = qmp.makefile('rwb',buffering=0)
        f.readline()
        def request(name, arguments=None):
            f.write((json.dumps({'execute':name, **({'arguments':arguments} if arguments else {})})+'\n').encode())
            while True:
                response = json.loads(f.readline())
                if 'error' in response:
                    raise RuntimeError(response)
                if 'return' in response:
                    return response['return']
        request('qmp_capabilities')
        request('screendump',{'filename':str(a.output.resolve()/'screen.ppm')})
        def touch(text):
            node = next(n for n in ET.fromstring(report['ui_xml']).iter('node')
                        if n.get('text','').casefold() == text.casefold())
            x1,y1,x2,y2 = map(int,re.findall(r'\d+',node.get('bounds')))
            request('input-send-event', {'events': [
                {'type':'abs','data':{'axis':'x','value':int((x1+x2)/2*32767/360)}},
                {'type':'abs','data':{'axis':'y','value':int((y1+y2)/2*32767/800)}},
                {'type':'btn','data':{'button':'left','down':True}}]})
            time.sleep(0.2)
            request('input-send-event', {'events':[
                {'type':'btn','data':{'button':'left','down':False}}]})
        touch('Count touch')
        time.sleep(5)
        exchange('uiautomator dump /data/local/tmp/window.xml',timeout=300)
        report['ui_xml_after_touch'] = exchange('cat /data/local/tmp/window.xml')
        report['usb_touch_confirmed'] = 'Touches: 1' in report['ui_xml_after_touch']
        assert report['usb_touch_confirmed'], 'USB HID did not change the touch counter'
        touch('Play tone')
        time.sleep(10)
    report['dynamic_executable_mapping_guard_passed'] = True
    log('[NoJIT] Boot/install/resumed/USB touch checks passed; iPhone/Metal still require device validation')
finally:
    report['elapsed_seconds'] = round(time.monotonic()-started,1)
    if bridge:
        bridge.close()
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    stderr.close()
    try:
        with wave.open(str(a.output/'audio.wav'),'rb') as wav:
            while data := wav.readframes(48000):
                if any(data):
                    report['guest_audio_confirmed'] = True
                    break
    except (OSError, EOFError, wave.Error):
        pass
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
