from collections import defaultdict
import threading


class EventBus:
    """Simple observer pattern: synchronous sequential execution of handlers."""

    def __init__(self):
        self._handlers = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event_name: str, handler):
        with self._lock:
            self._handlers[event_name].append(handler)

    def publish(self, event_name: str, payload: dict = None):
        # execute handlers in order
        handlers = []
        with self._lock:
            handlers = list(self._handlers.get(event_name, []))
        for h in handlers:
            try:
                h(payload or {})
            except Exception as e:
                print(f"Event handler error for {event_name}: {e}")


_bus = EventBus()

def get_event_bus():
    return _bus
