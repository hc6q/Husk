import unittest
from freezer_state import wait_disabled

class FreezerTests(unittest.TestCase):
    def test_async_observer(self):
        replies = iter(['Freezer settings\n use_freezer=true\n Apps frozen: 0',
                        'Freezer settings\n use_freezer=false\n Apps frozen: 0'])
        calls = []
        def exchange(cmd, **kwargs):
            calls.append(cmd)
            return next(replies)
        wait_disabled(exchange, lambda _: None, pause=lambda _: None)
        self.assertEqual(calls, ['dumpsys activity cao'] * 2)

    def test_wrong_dump_rejected(self):
        with self.assertRaises(RuntimeError):
            wait_disabled(lambda *a, **k: 'ACTIVITY MANAGER RUNNING PROCESSES', lambda _: None)

    def test_frozen_residual_rejected(self):
        ticks = iter([0, 0, 0, 181, 181])
        with self.assertRaises(TimeoutError):
            wait_disabled(lambda *a, **k: 'Freezer settings\n use_freezer=false\n Apps frozen: 1',
                          lambda _: None, clock=lambda: next(ticks))

    def test_command_timeout_not_replayed(self):
        calls = []
        def exchange(*a, **k):
            calls.append(a)
            raise TimeoutError()
        with self.assertRaises(TimeoutError):
            wait_disabled(exchange, lambda _: None)
        self.assertEqual(len(calls), 1)

if __name__ == '__main__':
    unittest.main()
