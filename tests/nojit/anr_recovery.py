"""Bounded, observable platform dialog recovery for host experiments only.

Recognize the actual captured dialog before clicking its button through
USB HID. This never constitutes APK/input acceptance; the visible counter must
still change afterwards. Only the explicitly identified Bluetooth crash dialog may close its guest app.
No Android timeout or boot flag is changed.
"""
import csv
import io
import re


def wait_button(tsv):
    words = [row for row in csv.DictReader(io.StringIO(tsv), delimiter='\t')
             if row.get('level') == '5' and row.get('text', '').strip()]
    text = ' '.join(row['text'] for row in words).casefold()
    normalized = re.sub(r'[^a-z ]', '', text)
    bluetooth = 'bluetooth keeps stopping' in normalized
    if not bluetooth and not re.search(r'system u[il] isn.?t responding', normalized):
        raise ValueError('Captured screen does not confirm a supported platform dialog')
    label = 'close' if bluetooth else 'wait'
    buttons = [row for row in words if row['text'].casefold() == label
               and float(row['conf']) >= 50]
    if bluetooth:
        assert any(row['text'].casefold() == 'app' and float(row['conf']) >= 50
                   for row in words), 'Bluetooth dialog has no Close app button'
    if len(buttons) != 1:
        raise ValueError('Captured dialog has no unique confident Wait button')
    button = buttons[0]
    x = int(button['left']) + int(button['width']) / 2
    y = int(button['top']) + int(button['height']) / 2
    if not (0 <= x < 360 and 0 <= y < 800):
        raise ValueError('Wait button is outside the fixed guest framebuffer')
    return ('Close Bluetooth' if bluetooth else 'USB Wait'), x, y
