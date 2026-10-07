#!/usr/bin/env python3
"""Prepare persistent Android settings before a measured low-performance boot."""

DESKTOP_MODE_OVERRIDE = 'development_override_desktop_mode_features'


def stage_low_performance_boot(exchange, *, quiet_radio=False,
                               disable_bluetooth_package=False):
    """Persist only guest settings needed before the real reboot.

    The shipped snapshot is already booted, so SettingsProvider and PackageManager
    are available.  The caller must reset the VM after this function returns; no
    cached snapshot property is accepted as evidence for that following boot.
    """
    report = {}
    exchange(f'settings put global {DESKTOP_MODE_OVERRIDE} 0', timeout=180)
    value = exchange(
        f'settings get global {DESKTOP_MODE_OVERRIDE}', timeout=120).strip()
    if value != '0':
        raise RuntimeError(f'Desktop mode override was not persisted: {value!r}')
    report['guest_desktop_mode_disabled_before_reboot'] = True

    if quiet_radio:
        exchange(
            'settings put global bluetooth_on 0; '
            'settings put global ble_scan_always_enabled 0', timeout=180)
        if exchange('settings get global bluetooth_on', timeout=120).strip() != '0':
            raise RuntimeError('Guest Bluetooth setting was not disabled')
        report['guest_radio_disabled_before_reboot'] = True

    if disable_bluetooth_package:
        exchange('pm disable-user --user 0 com.android.bluetooth', timeout=300)
        disabled = exchange(
            'pm list packages -d com.android.bluetooth', timeout=180).splitlines()
        if 'package:com.android.bluetooth' not in disabled:
            raise RuntimeError('Guest Bluetooth package disable was not persisted')
        report['guest_bluetooth_package_disabled_before_reboot'] = True

    exchange('sync', timeout=180)
    return report
