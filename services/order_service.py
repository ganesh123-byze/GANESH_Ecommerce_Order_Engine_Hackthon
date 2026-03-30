import threading
from typing import List, Dict
from models.order import Order, OrderItem, OrderState
from services.product_service import ProductService
from services.payment_service import PaymentService
from utils.logger import get_logger
from utils.events import get_event_bus
from utils.idempotency import get_idempotency_store


class OrderService:
    def __init__(self):
        self._orders: Dict[str, Order] = {}
        self._lock = threading.Lock()
        self._product_service = ProductService.instance()
        self._payment = PaymentService()
        self.logger = get_logger()
        self.events = get_event_bus()
        self._idempotency = get_idempotency_store()

    def _validate_transition(self, current: OrderState, target: OrderState) -> bool:
        valid = {
            OrderState.CREATED: [OrderState.PENDING_PAYMENT, OrderState.CANCELLED, OrderState.FAILED],
            OrderState.PENDING_PAYMENT: [OrderState.PAID, OrderState.FAILED, OrderState.CANCELLED],
            OrderState.PAID: [OrderState.SHIPPED, OrderState.CANCELLED],
            OrderState.SHIPPED: [OrderState.DELIVERED],
        }
        if current == target:
            return True
        return target in valid.get(current, [])

    def view_orders(self):
        with self._lock:
            return {oid: {"user": o.user_id, "state": o.state.value, "total": o.total} for oid, o in self._orders.items()}

    def get_order(self, order_id: str):
        return self._orders.get(order_id)

    def _apply_discounts(self, items: List[OrderItem], coupon: str = None) -> float:
        subtotal = sum(i.price * i.qty for i in items)
        discount = 0.0
        if subtotal >= 1000:
            discount += 0.10 * subtotal
        # quantity >3 extra 5% per product-level? We'll interpret as overall if any item qty>3
        if any(i.qty > 3 for i in items):
            discount += 0.05 * subtotal
        if coupon == 'SAVE10':
            discount += 0.10 * subtotal
        if coupon == 'FLAT200':
            discount += 200
        total = max(0.0, subtotal - discount)
        return total

    def place_order(self, user_id: str, items: List[OrderItem], coupon: str = None, idempotency_key: str = None) -> Order:
        # idempotency
        if idempotency_key:
            if not self._idempotency.check_and_mark(idempotency_key):
                raise RuntimeError("Duplicate request")

        # Validate cart/stock by trying to commit reservation: atomic approach
        # We'll first ensure requested qty is reserved (assume CartService reserved before calling this)
        total = self._apply_discounts(items, coupon)
        order = Order.create(user_id=user_id, items=items, total=total, coupon=coupon)
        order.state = OrderState.PENDING_PAYMENT

        with self._lock:
            self._orders[order.id] = order

        # emit event with helpful payload for subscribers (user and total)
        self.events.publish('ORDER_CREATED', {'order_id': order.id, 'user_id': user_id, 'total': total})
        self.logger.log(f"ORDER_CREATED id={order.id} user={user_id} total={total}")

        # Validate committable for all items before attempting payment.
        for it in items:
            if not self._product_service.has_commitable(it.product_id, it.qty):
                # release any reservations and fail early
                for r in items:
                    self._product_service.release(r.product_id, r.qty)
                order.state = OrderState.FAILED
                with self._lock:
                    self._orders.pop(order.id, None)
                self.logger.log(f"ORDER_VALIDATION_FAILED id={order.id} user={user_id}")
                raise RuntimeError("Order validation failed: insufficient reserved/stock")

        # attempt payment
        ok = self._payment.charge(user_id, total)
        if not ok:
            # rollback: mark failed, release reservations and delete order
            order.state = OrderState.FAILED
            self.logger.log(f"ORDER_PAYMENT_FAILED id={order.id}")
            # release reserved stock
            for it in items:
                self._product_service.release(it.product_id, it.qty)
            # remove order
            with self._lock:
                self._orders.pop(order.id, None)
            self.events.publish('PAYMENT_FAILED', {'order_id': order.id})
            raise RuntimeError("Payment failed; transaction rolled back")

        # commit stock: subtract reserved and decrement stock
        for it in items:
            self._product_service.commit_reservation(it.product_id, it.qty)

        order.state = OrderState.PAID
        self.logger.log(f"ORDER_PAID id={order.id}")
        self.events.publish('PAYMENT_SUCCESS', {'order_id': order.id})
        return order

    def cancel_order(self, order_id: str):
        order = self._orders.get(order_id)
        if not order:
            raise KeyError("Order not found")
        if not self._validate_transition(order.state, OrderState.CANCELLED):
            raise RuntimeError("Invalid transition to CANCELLED")
        # restore stock
        for it in order.items:
            self._product_service.update_stock(it.product_id, it.qty)
        order.state = OrderState.CANCELLED
        self.logger.log(f"ORDER_CANCELLED id={order.id}")

    def return_product(self, order_id: str, product_id: str, qty: int):
        order = self._orders.get(order_id)
        if not order:
            raise KeyError("Order not found")
        # find item
        for it in order.items:
            if it.product_id == product_id:
                if qty > it.qty:
                    raise ValueError("Return qty exceeds purchased qty")
                it.qty -= qty
                refund = it.price * qty
                order.total -= refund
                # update stock
                self._product_service.update_stock(product_id, qty)
                self.logger.log(f"RETURN order={order_id} product={product_id} qty={qty} refund={refund}")
                return
        raise KeyError("Product not in order")
