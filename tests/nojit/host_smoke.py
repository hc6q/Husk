#!/usr/bin/env python3
"""Real Android/APK smoke test against the pinned Linux TCI build.

This validates the interpreter and guest, not iOS signing or Metal. Supply the
same vda image/firmware as Husk and disposable writable vars/userdata disks.
The mmap guard must be loaded into QEMU throughout this test.
"""
import argparse
from anr_recovery import wait_button
import hashlib
import json
import os
import platform
from pathlib import Path
import re
import socket
import shlex
import sys
import subprocess
import time
import xml.etree.ElementTree as ET
import wave

p = argparse.ArgumentParser()
p.add_argument('--qemu', type=Path, required=True)
p.add_argument('--backend', choices=('TCI','TCTI'), default='TCI')
p.add_argument('--guest', type=Path, required=True)
p.add_argument('--apk', type=Path, required=True)
p.add_argument('--package', default='org.husk.nojitsmoke')
p.add_argument('--ui-timeout', type=int, default=300)
p.add_argument('--platform-dialog-recovery-attempts', type=int, choices=range(4), default=0,
               help='Experimental bounded USB clicks on captured System UI/Bluetooth dialogs')
p.add_argument('--guard', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--timeout', type=int, default=7200)
p.add_argument('--memory', type=int, default=2048)
p.add_argument('--cpus', type=int, choices=(1,2,4), default=4)
p.add_argument('--threads', choices=('single','multi'), default='single')
p.add_argument('--snapshot', help='Restore the original userdata snapshot through QMP')
p.add_argument('--file-ram', action='store_true')
p.add_argument('--interactive', action='store_true', help='Read shell/QMP JSON commands after install')
p.add_argument('--qmp-socket', type=Path, help='Optional second QMP endpoint for live display/input probes')
p.add_argument('--icount', action='store_true', help='Experimental instruction clock')
p.add_argument('--icount-shift', type=int, choices=range(0,11), default=0, help='Experimental ns per instruction exponent')
p.add_argument('--snapshot-clock-aligned', action='store_true', help='Requires the experimental timer migration patch')
a = p.parse_args()
if a.icount and a.threads == 'multi':
    p.error('--icount is incompatible with MTTCG')
if a.icount_shift and not a.icount:
    p.error('--icount-shift requires --icount')
if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+', a.package):
    p.error('--package must be an Android package ID')
if a.icount and a.snapshot and not a.snapshot_clock_aligned:
    p.error('--icount cannot restore the wall-clock snapshot without alignment')
if a.snapshot_clock_aligned and not (a.icount and a.snapshot):
    p.error('--snapshot-clock-aligned requires --icount and --snapshot')
if a.snapshot and a.cpus != 4:
    p.error('the official snapshot requires four vCPUs')
a.output.mkdir(parents=True, exist_ok=True)
report = {'platform': f'Linux {platform.machine()} host / Android ARM64 guest', 'backend': a.backend,
          'boot_completed': False, 'apk_installed': False, 'apk_resumed': False,
          'usb_touch_confirmed': False, 'guest_audio_confirmed': False,
          'ios_device_tested': False, 'package_id': a.package,
          'apk_sha256': hashlib.sha256(a.apk.read_bytes()).hexdigest(),
          'ui_timeout_seconds': a.ui_timeout}
report.update(cpu_threads=a.threads, vcpus=a.cpus, memory_mib=a.memory)
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
        'max,pauth-impdef=on,sve=off,sme=off', '-smp', str(a.cpus), '-m', str(a.memory),
        '-accel', f'tcg,tb-size=128,thread={a.threads},split-wx=off',
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
if a.qmp_socket:
    endpoint = a.qmp_socket.resolve()
    if endpoint.exists() or ',' in str(endpoint):
        p.error('--qmp-socket must be an unused path without commas')
    endpoint.parent.mkdir(parents=True, exist_ok=True)
    args += ['-qmp', f'unix:{endpoint},server=on,wait=off']
if a.snapshot:
    args += ['-S']
    # The shipped snapshot has no virtio-sound device; preserve its topology.
    index = args.index('-audiodev')
    del args[index:index+4]
if a.icount:
    clock = f'shift={a.icount_shift},sleep=off,align=off'
    args += ['-icount', clock, '-rtc', 'clock=vm']
    report['instruction_clock'] = clock
env = dict(os.environ, LD_PRELOAD=str(a.guard.resolve()))
stderr = (a.output/'qemu.log').open('w')
proc = subprocess.Popen(args, stdout=stderr, stderr=stderr, env=env)
bridge = None
sequence = 0
def audit_maps(stage):
    process_path = Path(f'/proc/{proc.pid}')
    expected = str(qemu).encode()
    try:
        matching = (process_path/'cmdline').read_bytes().split(b'\0')[0] == expected
    except FileNotFoundError:
        matching = False
    if not matching:
        # Some execution sandboxes expose a parent-namespace /proc mount.
        # Require both the namespace PID and exact executable, never audit
        # an unrelated host process merely because its PID has the same number.
        candidates = []
        for path in Path('/proc').iterdir():
            if not path.name.isdecimal():
                continue
            try:
                status = (path/'status').read_text()
                ids = next(line.split()[1:] for line in status.splitlines()
                           if line.startswith('NSpid:'))
                if int(ids[-1]) == proc.pid and (path/'cmdline').read_bytes().split(b'\0')[0] == expected:
                    candidates.append(path)
            except (OSError, StopIteration, ValueError):
                continue
        assert len(candidates) == 1, 'Could not identify the actual QEMU mappings'
        process_path = candidates[0]
    mappings = (process_path/'maps').read_text()
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
        with control, control.makefile('rwb',buffering=0) as stream:
            control.settimeout(600)  # Loading several GiB can hold the QMP main loop.
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
            if a.snapshot_clock_aligned:
                text = (a.output/'qemu.log').read_text()
                match = re.search(r'\[NoJIT\] Snapshot clock aligned at (\d+) ns', text)
                assert match, 'QEMU did not confirm the snapshot clock alignment'
                report['snapshot_clock_ns'] = int(match.group(1))
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
                assert f'[NoJIT] {a.backend} bytecode buffer RW' in (a.output/'qemu.log').read_text(), 'Expected interpreter backend not confirmed by allocator'
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
    if a.interactive:
        log('Interactive probe: JSON shell/qmp commands; {"continue":true} resumes acceptance')
        for line in sys.stdin:
            command = json.loads(line)
            if command.get('continue'):
                break
            if 'shell' in command:
                exchange(command['shell'], timeout=command.get('timeout',900))
            elif 'qmp' in command:
                with socket.create_connection(('127.0.0.1',15598),timeout=180) as control, control.makefile('rwb',buffering=0) as stream:
                    stream.readline()
                    def probe(name, arguments=None):
                        stream.write((json.dumps({'execute':name, **({'arguments':arguments} if arguments else {})})+'\n').encode())
                        while True:
                            response = json.loads(stream.readline())
                            if 'error' in response:
                                raise RuntimeError(response)
                            if 'return' in response:
                                return response['return']
                    probe('qmp_capabilities')
                    print(json.dumps(probe(command['qmp'],command.get('arguments'))), flush=True)
    exchange('settings put global device_provisioned 1; settings put secure user_setup_complete 1')
    exchange('input keyevent 82')
    log('[NoJIT] Launching package')
    launcher = exchange('cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.LAUNCHER '+shlex.quote(a.package),timeout=300).strip().splitlines()[-1]
    assert launcher.startswith(a.package+'/'), launcher
    exchange('am start -n '+shlex.quote(launcher), timeout=900)
    for _ in range(60):
        activity = exchange('dumpsys activity activities | grep -E "mResumedActivity|topResumedActivity" || true',timeout=180)
        if a.package+'/' in activity:
            report['apk_resumed'] = True
            break
        time.sleep(5)
    assert report['apk_resumed'], 'APK was installed but did not resume'
    audit_maps('apk')
    report['anr_recovery'] = []
    for attempt in range(a.platform_dialog_recovery_attempts+1):
        # Remove any old dump so a failed UI dump cannot accept stale content.
        exchange('rm -f /data/local/tmp/window.xml')
        dump = exchange('uiautomator dump /data/local/tmp/window.xml',timeout=a.ui_timeout)
        xml = exchange('cat /data/local/tmp/window.xml 2>/dev/null || true')
        (a.output/f'ui-attempt-{attempt}.txt').write_text(dump+'\n'+xml)
        try:
            nodes = ET.fromstring(xml).iter('node')
            ready = any(n.get('text','').casefold() == 'count touch' and
                        n.get('package') == a.package for n in nodes)
        except ET.ParseError:
            ready = False
        if ready:
            report['ui_xml'] = xml
            break
        if attempt == a.platform_dialog_recovery_attempts:
            raise RuntimeError('No current fixture UI; APK resumed is insufficient')
        with socket.create_connection(('127.0.0.1',15598),timeout=180) as control, control.makefile('rwb',buffering=0) as stream:
            stream.readline()
            def recover(name, arguments=None):
                stream.write((json.dumps({'execute':name, **({'arguments':arguments} if arguments else {})})+'\n').encode())
                while True:
                    response = json.loads(stream.readline())
                    if 'error' in response:
                        raise RuntimeError(response)
                    if 'return' in response:
                        return response['return']
            recover('qmp_capabilities')
            screen = a.output.resolve()/f'anr-before-{attempt}.ppm'
            recover('screendump', {'filename':str(screen)})
            ocr = subprocess.check_output(['tesseract',str(screen),'stdout','tsv'],text=True)
            (a.output/f'anr-before-{attempt}.tsv').write_text(ocr)
            action, x, y = wait_button(ocr)  # Fail closed for an unrelated dialog.
            if action == 'Close Bluetooth':
                exchange('svc bluetooth disable')
                bluetooth_state = exchange('settings get global bluetooth_on').strip()
                assert bluetooth_state == '0', 'Guest Bluetooth disable was not confirmed'
                report['guest_bluetooth_disabled'] = True
            report['anr_recovery'].append({'attempt':attempt+1,'action':action,
                                          'x':x,'y':y,'screen':screen.name})
            log(f'[NoJIT] Captured platform dialog; {action} recovery {attempt+1}')
            recover('input-send-event', {'events': [
                {'type':'abs','data':{'axis':'x','value':int(x*32767/360)}},
                {'type':'abs','data':{'axis':'y','value':int(y*32767/800)}},
                {'type':'btn','data':{'button':'left','down':True}}]})
            time.sleep(0.2)
            recover('input-send-event', {'events':[
                {'type':'btn','data':{'button':'left','down':False}}]})
            time.sleep(15)
            recover('screendump', {'filename':str(a.output.resolve()/f'anr-after-{attempt}.ppm')})
    with socket.create_connection(('127.0.0.1',15598),timeout=180) as qmp, qmp.makefile('rwb',buffering=0) as f:
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
        exchange('uiautomator dump /data/local/tmp/window.xml',timeout=a.ui_timeout)
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
    if proc.poll() is None:
        try:
            with socket.create_connection(('127.0.0.1',15598),timeout=60) as control, control.makefile('rwb',buffering=0) as stream:
                stream.readline()
                def diagnostic(name, arguments=None):
                    stream.write((json.dumps({'execute':name, **({'arguments':arguments} if arguments else {})})+'\n').encode())
                    while True:
                        response = json.loads(stream.readline())
                        if 'error' in response:
                            raise RuntimeError(response)
                        if 'return' in response:
                            return response['return']
                diagnostic('qmp_capabilities')
                report['qmp_status'] = diagnostic('query-status')
                for name in ('info cpus', 'info registers', 'info network'):
                    report[name] = diagnostic('human-monitor-command', {'command-line':name})
                diagnostic('screendump', {'filename':str(a.output.resolve()/'final-screen.ppm')})
        except (OSError, ValueError, RuntimeError) as error:
            report['qmp_diagnostic_error'] = str(error)
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
    print(json.dumps(report, indent=2), flush=True)
    for name in ('qemu.log', 'serial.log'):
        path = a.output/name
        if path.exists():
            print(f'--- {name} (last 60 lines) ---', flush=True)
            print('\n'.join(path.read_text(errors='replace').splitlines()[-60:]), flush=True)
