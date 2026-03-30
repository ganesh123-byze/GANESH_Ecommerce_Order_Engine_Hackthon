from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List, Optional
from uuid import uuid4, UUID
import logging

from app.services.product_service import get_product_service, ProductService
from app.services.payment_service import get_payment_service, PaymentService
from app.utils.event_bus import get_event_bus
from app.utils.audit_logger import get_audit_logger

logger = logging.getLogger("app")


@dataclass
class OrderRecord:
    id: UUID
    user_id: str
    items: List[Dict]
    total: float
    state: str = "CREATED"


class OrderService:
    def __init__(self):
        self._lock = Lock()
        self._orders: Dict[UUID, OrderRecord] = {}
        self._idempotency: Dict[str, UUID] = {}
        self._product_svc: ProductService = get_product_service()
        self._payment: PaymentService = get_payment_service()
        self._events = get_event_bus()
        self._audit = get_audit_logger()

    def place_order(self, user_id: str, items: List[Dict], coupon: Optional[str] = None, idempotency_key: Optional[str] = None) -> OrderRecord:
        # idempotency
        if idempotency_key and idempotency_key in self._idempotency:
            oid = self._idempotency[idempotency_key]
            return self._orders[oid]

        # validate cart items
        total = 0.0
        for it in items:
            # ensure product exists
            p = self._product_svc.get(it['product_id'])
            if p is None:
                raise Exception("product not found")
            total += it['price'] * it['quantity']

        # apply simple coupons
        if coupon == 'SAVE10' and total >= 1000:
            total *= 0.9
        elif coupon == 'FLAT200' and total >= 200:
            total -= 200

        oid = uuid4()
        order = OrderRecord(id=oid, user_id=user_id, items=items, total=total, state='PENDING_PAYMENT')

        with self._lock:
            self._orders[oid] = order
            if idempotency_key:
                self._idempotency[idempotency_key] = oid

        # publish ORDER_CREATED
        self._audit.log(f"ORDER_CREATED id={oid} user={user_id} total={total}")
        self._events.publish("ORDER_CREATED", order_id=str(oid), user_id=user_id, total=total)

        # process payment
        ok = self._payment.charge(user_id, total, idempotency_key)
        if not ok:
            order.state = 'FAILED'
            # release reserved stock
            for it in items:
                self._product_svc.release(it['product_id'], it['quantity'])
            self._audit.log(f"ORDER_PAYMENT_FAILED id={oid}")
            self._events.publish("PAYMENT_FAILED", order_id=str(oid), user_id=user_id)
            raise Exception("payment failed")

        # payment succeeded
        order.state = 'PAID'
        self._audit.log(f"ORDER_PAID id={oid}")
        self._events.publish("PAYMENT_SUCCESS", order_id=str(oid), user_id=user_id, total=total)

        # log commit (stock already decremented on reserve)
        for it in items:
            self._audit.log(f"COMMIT product={it['product_id']} qty={it['quantity']}")
            self._events.publish("INVENTORY_UPDATED", product_id=str(it['product_id']), qty=it['quantity'])

        return order

    def view_orders(self) -> List[OrderRecord]:
        with self._lock:
            return list(self._orders.values())

    def get_order(self, oid: UUID) -> Optional[OrderRecord]:
        with self._lock:
            return self._orders.get(oid)

    def cancel_order(self, oid: UUID) -> bool:
        with self._lock:
            o = self._orders.get(oid)
            if o is None:
                raise Exception('order not found')
            if o.state == 'CANCELLED':
                raise Exception('order already cancelled')
            # allow cancel and restore stock
            o.state = 'CANCELLED'

        for it in o.items:
            self._product_svc.release(it['product_id'], it['quantity'])
        logger.info(f"ORDER_CANCELLED id={oid}")
        return True

    def return_product(self, oid: UUID, product_id: UUID, qty: int) -> bool:
        with self._lock:
            o = self._orders.get(oid)
            if o is None:
                raise Exception('order not found')
        # release stock
        self._product_svc.release(product_id, qty)
        logger.info(f"RETURN order={oid} product={product_id} qty={qty}")
        return True


_order_svc: Optional[OrderService] = None


def get_order_service() -> OrderService:
    global _order_svc
    if _order_svc is None:
        _order_svc = OrderService()
    return _order_svc
