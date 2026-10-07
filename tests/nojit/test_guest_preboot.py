#!/usr/bin/env python3
import unittest

from guest_preboot import DESKTOP_MODE_OVERRIDE, stage_low_performance_boot


class GuestPrebootTests(unittest.TestCase):
    def test_stages_desktop_and_absent_bluetooth_before_reboot(self):
        commands = []

        def exchange(command, timeout):
            commands.append((command, timeout))
            if command == f'settings get global {DESKTOP_MODE_OVERRIDE}':
                return '0\n'
            if command == 'settings get global bluetooth_on':
                return '0\n'
            if command == 'pm list packages -d com.android.bluetooth':
                return 'package:com.android.bluetooth\n'
            return ''

        report = stage_low_performance_boot(
            exchange, quiet_radio=True, disable_bluetooth_package=True)
        self.assertEqual(report, {
            'guest_desktop_mode_disabled_before_reboot': True,
            'guest_radio_disabled_before_reboot': True,
            'guest_bluetooth_package_disabled_before_reboot': True,
        })
        self.assertEqual(commands[-1], ('sync', 180))
        self.assertLess(
            commands.index((
                f'settings put global {DESKTOP_MODE_OVERRIDE} 0', 180)),
            commands.index(('sync', 180)))

    def test_rejects_unconfirmed_desktop_override(self):
        def exchange(command, timeout):
            if command.startswith('settings get'):
                return '-1\n'
            return ''

        with self.assertRaisesRegex(RuntimeError, 'Desktop mode override'):
            stage_low_performance_boot(exchange)


if __name__ == '__main__':
    unittest.main()
