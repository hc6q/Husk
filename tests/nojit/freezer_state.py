"""Verify the asynchronous Android cached-freezer override without replaying writes."""
import re
import time

def wait_disabled(exchange, save, timeout=180, clock=time.monotonic, pause=time.sleep):
    deadline = clock() + timeout
    while clock() < deadline:
        state = exchange('dumpsys activity cao', timeout=max(1, deadline-clock()))
        save(state)
        disabled = re.search(r'^\s*use_freezer=false\s*$', state, re.M)
        empty = re.search(r'^\s*Apps frozen: 0\s*$', state, re.M)
        if disabled and empty:
            return
        # A partial/timeout dump cannot establish effective state.
        if 'Freezer settings' not in state:
            raise RuntimeError('Cached optimizer dump missing Freezer settings')
        remaining = deadline - clock()
        if remaining > 0:
            pause(min(2, remaining))
    raise TimeoutError('Freezer did not become disabled with zero frozen processes')
