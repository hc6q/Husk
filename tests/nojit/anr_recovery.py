"""Bounded, observable System UI ANR recovery for host experiments only.

Recognize the actual captured dialog before clicking its Wait button through
USB HID. This never constitutes APK/input acceptance; the visible counter must
still change afterwards. No Android timeout, process, or boot flag is changed.
"""
import csv
import io
import re


def wait_button(tsv):
    words = [row for row in csv.DictReader(io.StringIO(tsv), delimiter='\t')
             if row.get('level') == '5' and row.get('text', '').strip()]
    text = ' '.join(row['text'] for row in words).casefold()
    normalized = re.sub(r'[^a-z ]', '', text)
    if not re.search(r'system u[il] isn.?t responding', normalized):
        raise ValueError('Captured screen does not confirm the System UI ANR dialog')
    buttons = [row for row in words if row['text'].casefold() == 'wait'
               and float(row['conf']) >= 50]
    if len(buttons) != 1:
        raise ValueError('Captured dialog has no unique confident Wait button')
    button = buttons[0]
    x = int(button['left']) + int(button['width']) / 2
    y = int(button['top']) + int(button['height']) / 2
    if not (0 <= x < 360 and 0 <= y < 800):
        raise ValueError('Wait button is outside the fixed guest framebuffer')
    return x, y
