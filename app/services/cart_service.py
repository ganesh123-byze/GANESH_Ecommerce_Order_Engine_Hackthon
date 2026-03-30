from threading import Lock, Timer
from typing import Dict, DefaultDict, Tuple
from collections import defaultdict
from uuid import UUID

from app.services.product_service import get_product_service, ProductService
from app.utils.audit_logger import get_audit_logger
from app.utils.event_bus import get_event_bus

RESERVATION_EXPIRY_SECONDS = 30


class CartService:
    def __init__(self):
        self._lock = Lock()
        # user_id -> {product_id: qty}
        self._carts: Dict[str, Dict[UUID, int]] = defaultdict(dict)
        self._product_svc: ProductService = get_product_service()
        # timers keyed by (user_id, product_id)
        self._timers: Dict[Tuple[str, UUID], Timer] = {}
        self._audit = get_audit_logger()
        self._events = get_event_bus()

    def get_cart(self, user_id: str) -> Dict[UUID, int]:
        with self._lock:
            # return a shallow copy
            return dict(self._carts.get(user_id, {}))

    def add_item(self, user_id: str, product_id: UUID, qty: int) -> bool:
        if qty <= 0:
            return False
        # Reserve first
        reserved = self._product_svc.reserve(product_id, qty)
        if not reserved:
            return False

        with self._lock:
            cur = self._carts.setdefault(user_id, {})
            cur[product_id] = cur.get(product_id, 0) + qty
            # cancel any existing timer for this item
            self._cancel_timer(user_id, product_id)
            # start expiry timer
            t = Timer(RESERVATION_EXPIRY_SECONDS, self._expire_reservation, args=(user_id, product_id, qty))
            self._timers[(user_id, product_id)] = t
            t.daemon = True
            t.start()

        self._audit.log(f"{user_id} added {product_id} qty={qty} to cart")
        self._events.publish("INVENTORY_RESERVED", user_id=user_id, product_id=str(product_id), qty=qty)
        return True

    def remove_item(self, user_id: str, product_id: UUID) -> bool:
        with self._lock:
            cur = self._carts.get(user_id)
            if not cur or product_id not in cur:
                return False
            qty = cur.pop(product_id)
            # cancel timer
            self._cancel_timer(user_id, product_id)
        # release reserved stock
        self._product_svc.release(product_id, qty)
        self._audit.log(f"{user_id} removed {product_id} qty={qty} from cart")
        self._events.publish("INVENTORY_RELEASED", user_id=user_id, product_id=str(product_id), qty=qty)
        return True

    def update_quantity(self, user_id: str, product_id: UUID, new_qty: int) -> bool:
        if new_qty < 0:
            return False
        with self._lock:
            cur = self._carts.setdefault(user_id, {})
            old_qty = cur.get(product_id, 0)
            if new_qty == old_qty:
                return True
            # if increasing, try to reserve additional
            delta = new_qty - old_qty
        if delta > 0:
            if not self._product_svc.reserve(product_id, delta):
                return False
        elif delta < 0:
            # release the difference
            self._product_svc.release(product_id, -delta)
        with self._lock:
            if new_qty == 0:
                cur.pop(product_id, None)
                self._cancel_timer(user_id, product_id)
            else:
                cur[product_id] = new_qty
                # restart timer
                self._cancel_timer(user_id, product_id)
                t = Timer(RESERVATION_EXPIRY_SECONDS, self._expire_reservation, args=(user_id, product_id, new_qty))
                t.daemon = True
                self._timers[(user_id, product_id)] = t
                t.start()
        self._audit.log(f"{user_id} updated {product_id} qty={new_qty} in cart")
        return True

    def clear_cart(self, user_id: str) -> None:
        with self._lock:
            cur = self._carts.pop(user_id, {})
            # cancel timers for this user's items
            for pid in list(cur.keys()):
                self._cancel_timer(user_id, pid)
        # release all reserved
        for pid, qty in cur.items():
            self._product_svc.release(pid, qty)

        if cur:
            self._audit.log(f"{user_id} cleared cart and released {len(cur)} items")

    def _cancel_timer(self, user_id: str, product_id: UUID) -> None:
        key = (user_id, product_id)
        t = self._timers.pop(key, None)
        if t:
            try:
                t.cancel()
            except Exception:
                pass

    def _expire_reservation(self, user_id: str, product_id: UUID, qty: int) -> None:
        # called in timer thread
        with self._lock:
            cur = self._carts.get(user_id)
            if not cur:
                return
            current_qty = cur.get(product_id, 0)
            # If user still has at least the qty reserved, expire it
            if current_qty >= qty:
                cur.pop(product_id, None)
                # remove timer entry
                self._timers.pop((user_id, product_id), None)
            else:
                # skip expiry if quantities changed/committed
                return
        # release reserved
        self._product_svc.release(product_id, qty)
        self._audit.log(f"RESERVATION_EXPIRE user={user_id} product={product_id} qty={qty}")
        self._events.publish("RESERVATION_EXPIRED", user_id=user_id, product_id=str(product_id), qty=qty)


_cart_svc: CartService | None = None


def get_cart_service() -> CartService:
    global _cart_svc
    if _cart_svc is None:
        _cart_svc = CartService()
    return _cart_svc
