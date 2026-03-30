from collections import deque, defaultdict
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, List

from app.utils.event_bus import get_event_bus
from app.utils.audit_logger import get_audit_logger


_flags = set()
_lock = Lock()


class FraudService:
    def __init__(self):
        self._orders_by_user: Dict[str, deque] = defaultdict(lambda: deque())
        self._high_value_threshold = 10000.0
        self._audit = get_audit_logger()
        self._events = get_event_bus()
        self._events.subscribe("ORDER_CREATED", self._on_order_created)

    def _on_order_created(self, event_name: str, payload: dict):
        user = payload.get('user_id')
        total = float(payload.get('total', 0))
        ts = datetime.utcnow()
        dq = self._orders_by_user[user]
        dq.append(ts)
        # drop older than 1 minute
        cutoff = ts - timedelta(minutes=1)
        while dq and dq[0] < cutoff:
            dq.popleft()
        # flag if 3 or more in last minute
        if len(dq) >= 3:
            with _lock:
                _flags.add(user)
                self._audit.log(f"FRAUD_FLAG user={user} reason=3_orders_min")
        # high value
        if total >= self._high_value_threshold:
            with _lock:
                _flags.add(user)
                self._audit.log(f"FRAUD_FLAG user={user} reason=high_value total={total}")


_svc: FraudService | None = None


def init_fraud_service():
    global _svc
    if _svc is None:
        _svc = FraudService()
    return _svc


def get_flags() -> List[str]:
    with _lock:
        return list(_flags)
