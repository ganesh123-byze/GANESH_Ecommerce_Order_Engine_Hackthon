import threading
from typing import Set


class IdempotencyStore:
    def __init__(self):
        self._used = set()
        self._lock = threading.Lock()

    def check_and_mark(self, key: str) -> bool:
        """Return True if key was new and mark it. Return False if already used."""
        with self._lock:
            if key in self._used:
                return False
            self._used.add(key)
            return True


_store = IdempotencyStore()

def get_idempotency_store():
    return _store
