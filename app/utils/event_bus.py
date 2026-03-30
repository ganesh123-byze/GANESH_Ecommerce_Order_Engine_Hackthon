from threading import Lock
from typing import Callable, Dict, List


class EventBus:
    def __init__(self):
        self._subs: Dict[str, List[Callable]] = {}
        self._lock = Lock()

    def subscribe(self, event_name: str, fn: Callable):
        with self._lock:
            self._subs.setdefault(event_name, []).append(fn)

    def publish(self, event_name: str, **payload):
        with self._lock:
            handlers = list(self._subs.get(event_name, []))
        for h in handlers:
            try:
                h(event_name, payload)
            except Exception:
                # subscribers should handle their own errors
                pass


_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
