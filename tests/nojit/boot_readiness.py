"""Bounded, read-only boot polling across guest-agent restarts.

Only immutable/getprop reads and crash-log collection run here. Install and
launch operations stay outside this loop and must never be replayed on timeout.
"""
import time


def wait_for_boot(connect, query, disconnect, alive, deadline, *,
                  low_performance=False, collect_crash=None, observe=None,
                  log=lambda message: None, clock=time.monotonic,
                  sleep=time.sleep):
    failures = 0
    last_crash = float('-inf')
    while clock() < deadline:
        if not alive():
            raise RuntimeError('QEMU exited while waiting for Android boot')
        try:
            connect(min(5, max(0.01, deadline-clock())))
            command = 'getprop sys.boot_completed'
            if low_performance:
                command += '; getprop ro.boot.low_perf; getprop ro.hw_timeout_multiplier'
            values = query(command, timeout=min(60, max(0.01, deadline-clock()))).splitlines()
            if observe:
                observe(values)
            if values and values[0].strip() == '1':
                if low_performance:
                    assert values[1:] == ['1', '50'], f'Low-performance properties not confirmed: {values!r}'
                return failures
            if collect_crash and clock()-last_crash >= 60:
                last_crash = clock()
                collect_crash(min(60, max(0.01, deadline-clock())))
        except (ConnectionError, OSError, TimeoutError) as error:
            failures += 1
            disconnect()
            log(f'[NoJIT] Boot read connection lost; reconnect within deadline: {error}')
        sleep(min(5, max(0, deadline-clock())))
    raise TimeoutError('Android did not complete boot within the original deadline')
