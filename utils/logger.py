import threading
import time


class AuditLogger:
    """Immutable append-only audit logger (in-memory). Thread-safe."""

    def __init__(self):
        self._lock = threading.Lock()
        self._entries = []

    def log(self, msg: str):
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        entry = f"[{ts}] {msg}"
        with self._lock:
            self._entries.append(entry)
        print(entry)

    def all(self):
        with self._lock:
            return list(self._entries)

# singleton
_logger = AuditLogger()

def get_logger():
    return _logger
