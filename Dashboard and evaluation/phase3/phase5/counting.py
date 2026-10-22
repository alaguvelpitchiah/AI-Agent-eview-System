import threading


class CountingAdapter:
    """Wraps an adapter and counts agent executions (used to measure cost)."""
    def __init__(self, inner):
        self._inner, self.runs, self._lock = inner, 0, threading.Lock()

    def run(self, *a, **k):
        with self._lock:
            self.runs += 1
        return self._inner.run(*a, **k)

    def __getattr__(self, name):
        return getattr(self._inner, name)
