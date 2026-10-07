import unittest
from boot_readiness import wait_for_boot


class BootReadinessTests(unittest.TestCase):
    def setup_clock(self):
        self.now = 0
        return lambda: self.now, lambda seconds: setattr(self, 'now', self.now+seconds)

    def test_disconnect_then_real_properties_required(self):
        clock, sleep = self.setup_clock()
        answers = iter([ConnectionError('agent restarted'), '\n1\n50\n', '1\n1\n50\n'])
        commands, drops = [], []
        def query(command, timeout):
            commands.append(command)
            answer = next(answers)
            if isinstance(answer, Exception):
                raise answer
            return answer
        failures = wait_for_boot(lambda timeout: None, query, lambda: drops.append(1),
            lambda: True, 30, low_performance=True, clock=clock, sleep=sleep)
        self.assertEqual(failures, 1)
        self.assertEqual(len(drops), 1)
        self.assertEqual(len(commands), 3)
        self.assertTrue(all(command.startswith('getprop ') for command in commands))

    def test_repeated_disconnect_cannot_extend_deadline(self):
        clock, sleep = self.setup_clock()
        def query(command, timeout):
            raise ConnectionError('offline')
        with self.assertRaises(TimeoutError):
            wait_for_boot(lambda timeout: None, query, lambda: None, lambda: True,
                12, clock=clock, sleep=sleep)
        self.assertEqual(self.now, 12)

    def test_snapshot_old_boot_flag_cannot_approve_new_profile(self):
        clock, sleep = self.setup_clock()
        with self.assertRaises(AssertionError):
            wait_for_boot(lambda timeout: None, lambda command, timeout: '1\n\n\n',
                lambda: None, lambda: True, 30, low_performance=True, clock=clock, sleep=sleep)

    def test_process_exit_is_not_a_reconnectable_error(self):
        clock, sleep = self.setup_clock()
        with self.assertRaises(RuntimeError):
            wait_for_boot(lambda timeout: self.fail('must not connect'),
                lambda command, timeout: self.fail('must not query'), lambda: None,
                lambda: False, 30, clock=clock, sleep=sleep)


if __name__ == '__main__':
    unittest.main()
