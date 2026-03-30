import time
from typing import Dict, Optional
from uuid import uuid4

from app.services.product_service import get_product_service


class PaymentService:
    def __init__(self):
        self.failure_mode = False

    def charge(self, user_id: str, amount: float, idempotency_key: Optional[str] = None) -> bool:
        # simulate latency
        time.sleep(0.05)
        if self.failure_mode:
            return False
        return True

    def set_failure_mode(self, val: bool):
        self.failure_mode = val


_payment_svc: Optional[PaymentService] = None


def get_payment_service() -> PaymentService:
    global _payment_svc
    if _payment_svc is None:
        _payment_svc = PaymentService()
    return _payment_svc
