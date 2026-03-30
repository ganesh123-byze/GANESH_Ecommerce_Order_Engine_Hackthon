import collections
import time
from utils.logger import get_logger
from utils.events import get_event_bus


class FraudService:
    """Basic fraud detector: flags users with too many orders in short window or high-value orders."""

    def __init__(self, order_threshold=3, window_seconds=60, high_value_threshold=10000.0):
        self.logger = get_logger()
        self._events = get_event_bus()
        self._orders = {}  # user_id -> deque of timestamps
        self._flags = []
        self.order_threshold = order_threshold
        self.window_seconds = window_seconds
        self.high_value_threshold = high_value_threshold
        # subscribe
        self._events.subscribe('ORDER_CREATED', self._on_order_created)

    def _on_order_created(self, payload):
        # payload expected: {order_id, user_id, total}
        user = payload.get('user_id')
        total = payload.get('total', 0)
        ts = time.time()
        dq = self._orders.setdefault(user, collections.deque())
        dq.append(ts)
        # expire old
        while dq and ts - dq[0] > self.window_seconds:
            dq.popleft()
        if len(dq) >= self.order_threshold:
            msg = f"FRAUD_FLAG user={user} reason=high_rate orders_in_{self.window_seconds}s={len(dq)}"
            self.logger.log(msg)
            self._flags.append({'user': user, 'reason': 'high_rate', 'count': len(dq), 'ts': ts})
        if total >= self.high_value_threshold:
            msg = f"FRAUD_FLAG user={user} reason=high_value order_total={total}"
            self.logger.log(msg)
            self._flags.append({'user': user, 'reason': 'high_value', 'total': total, 'ts': ts})


_fraud = None

def init_fraud_service():
    global _fraud
    if _fraud is None:
        _fraud = FraudService()
    return _fraud

def get_flags():
    global _fraud
    if _fraud is None:
        return []
    return list(_fraud._flags)
