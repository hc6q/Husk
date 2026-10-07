"""Validate the actual framebuffer and USB touch without UIAutomator.

This is an isolated host experiment. Raw frames and OCR are retained; resumed
Activity alone never passes. Recovery is bounded and explicitly reported.
"""
import csv
import io
import re
import socket
import json
import subprocess
import time
from anr_recovery import wait_button


def fixture_button(tsv, count, label):
    rows = [r for r in csv.DictReader(io.StringIO(tsv), delimiter='\t')
            if r.get('level') == '5' and r.get('text', '').strip()]
    text = ' '.join(r['text'] for r in rows).casefold()
    text = re.sub(r'[^a-z0-9 ]', '', text)
    if 'responding' in text or 'keeps stopping' in text:
        raise ValueError('Platform dialog still covers the fixture')
    if 'husk nojit android app running' not in text:
        raise ValueError('Fixture caption is not visible')
    counters = [(a, b) for a, b in zip(rows, rows[1:])
                if a['text'].casefold().rstrip(':') == 'touches'
                and b['text'] == str(count)
                and float(a['conf']) >= 50 and float(b['conf']) >= 50]
    if len(counters) != 1:
        raise ValueError('Expected counter is not confidently visible')
    lines = {}
    for row in rows:
        key = tuple(row[k] for k in ('page_num','block_num','par_num','line_num'))
        lines.setdefault(key, []).append(row)
    matches = [line for line in lines.values()
               if ' '.join(r['text'] for r in line).casefold() == label.casefold()
               and all(float(r['conf']) >= 50 for r in line)]
    if len(matches) != 1:
        raise ValueError('Fixture button is not uniquely visible')
    line = matches[0]
    left = min(int(r['left']) for r in line)
    top = min(int(r['top']) for r in line)
    right = max(int(r['left'])+int(r['width']) for r in line)
    bottom = max(int(r['top'])+int(r['height']) for r in line)
    x, y = (left+right)/2, (top+bottom)/2
    if not (0 <= x < 360 and 0 <= y < 800):
        raise ValueError('Button is outside the guest framebuffer')
    return x, y


def verify(args, report, exchange, log):
    report['ui_validation'] = 'raw framebuffer OCR and USB HID'
    report['platform_dialog_recovery'] = []
    with socket.create_connection(('127.0.0.1',15598),timeout=180) as control, control.makefile('rwb',buffering=0) as stream:
        stream.readline()
        def request(name, arguments=None):
            stream.write((json.dumps({'execute':name, **({'arguments':arguments} if arguments else {})})+'\n').encode())
            while True:
                response = json.loads(stream.readline())
                if 'error' in response:
                    raise RuntimeError(response)
                if 'return' in response:
                    return response['return']
        request('qmp_capabilities')
        def capture(name):
            path = args.output.resolve()/(name+'.ppm')
            request('screendump', {'filename':str(path)})
            text = subprocess.check_output(['tesseract',str(path),'stdout','--psm','11','tsv'],text=True)
            (args.output/(name+'.tsv')).write_text(text)
            return text
        def touch(x, y):
            request('input-send-event', {'events':[
                {'type':'abs','data':{'axis':'x','value':int(x*32767/360)}},
                {'type':'abs','data':{'axis':'y','value':int(y*32767/800)}},
                {'type':'btn','data':{'button':'left','down':True}}]})
            time.sleep(0.2)
            request('input-send-event', {'events':[
                {'type':'btn','data':{'button':'left','down':False}}]})
        clicks = 0
        for phase, count, label in [('before-touch',0,'Count touch'),('after-touch',1,'Play tone')]:
            deadline = time.monotonic()+args.ui_timeout
            frame = 0
            while time.monotonic() < deadline:
                text = capture(f'{phase}-{frame}')
                frame += 1
                try:
                    x, y = fixture_button(text, count, label)
                    report['framebuffer_'+phase] = f'{phase}-{frame-1}.ppm'
                    break
                except ValueError as error:
                    report['last_framebuffer_error'] = str(error)
                try:
                    action, x, y = wait_button(text)
                except ValueError:
                    time.sleep(10)
                    continue
                if clicks >= args.platform_dialog_recovery_attempts:
                    # Bound clicks, not observation. A slow interpreter can
                    # drain the UI queue after the last permitted recovery.
                    # Keep requiring a fresh frame and the exact counter.
                    report['platform_dialog_recovery_exhausted'] = True
                    time.sleep(10)
                    continue
                if action == 'Close Bluetooth':
                    exchange('svc bluetooth disable')
                    assert exchange('settings get global bluetooth_on').strip() == '0'
                    report['guest_bluetooth_disabled'] = True
                report['platform_dialog_recovery'].append(dict(phase=phase,action=action,x=x,y=y))
                log(f'[NoJIT] Framebuffer recovery: {action}')
                touch(x, y)
                clicks += 1
                time.sleep(15)
            else:
                raise TimeoutError('Actual fixture framebuffer did not reach counter '+str(count))
            touch(x, y)
            time.sleep(10)
        report['usb_touch_confirmed'] = True
        report.pop('last_framebuffer_error', None)
        log('[NoJIT] Raw framebuffer counter changed from 0 to 1 via USB HID')
