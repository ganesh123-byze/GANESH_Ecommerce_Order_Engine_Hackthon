from datetime import datetime
from threading import Lock
from typing import List, Dict


class AuditLogger:
    def __init__(self):
        self._lock = Lock()
        self._entries: List[Dict] = []

    def log(self, message: str, **meta):
        entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "message": message,
            "meta": meta,
        }
        with self._lock:
            self._entries.append(entry)

    def all(self) -> List[Dict]:
        with self._lock:
            return list(self._entries)


_audit: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    global _audit
    if _audit is None:
        _audit = AuditLogger()
    return _audit
