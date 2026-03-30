import threading
import time
from typing import Dict
from models.cart import Cart, CartItem
from services.product_service import ProductService
from utils.logger import get_logger


class CartService:
    def __init__(self):
        self._carts: Dict[str, Cart] = {}
        self._lock = threading.Lock()
        self._product_service = ProductService.instance()
        self.logger = get_logger()
        # expiry timers: (user_id, product_id) -> timer
        self._expiry = {}

    def _ensure_cart(self, user_id: str) -> Cart:
        with self._lock:
            if user_id not in self._carts:
                self._carts[user_id] = Cart(user_id=user_id)
            return self._carts[user_id]

    def add_to_cart(self, user_id: str, product_id: str, qty: int, reserve_seconds: int = 30) -> bool:
        product = self._product_service.get(product_id)
        if not product:
            return False
        # try to reserve
        ok = self._product_service.reserve(product_id, qty)
        if not ok:
            return False
        cart = self._ensure_cart(user_id)
        cart.add_item(CartItem(product_id=product.id, name=product.name, price=product.price, qty=qty))
        self.logger.log(f"{user_id} added {product_id} qty={qty} to cart")

        # schedule expiry
        key = (user_id, product_id)
        if key in self._expiry:
            self._expiry[key].cancel()
        timer = threading.Timer(reserve_seconds, self._reservation_expiry, args=(user_id, product_id, qty))
        self._expiry[key] = timer
        timer.start()
        return True

    def _reservation_expiry(self, user_id, product_id, qty):
        # release reserved stock and remove item from cart partially
        try:
            # Only release if there is still reserved quantity for this product
            reserved = self._product_service.get_reserved(product_id)
            if reserved >= qty:
                self._product_service.release(product_id, qty)
                cart = self._carts.get(user_id)
                if cart:
                    cart.remove_item(product_id, qty)
                self.logger.log(f"RESERVATION_EXPIRE user={user_id} product={product_id} qty={qty}")
            else:
                # reservation already committed or released; skip noisy release
                self.logger.log(f"RESERVATION_EXPIRE_SKIPPED user={user_id} product={product_id} qty={qty} reserved_now={reserved}")
        finally:
            self._expiry.pop((user_id, product_id), None)

    def remove_from_cart(self, user_id: str, product_id: str, qty: int = None):
        cart = self._carts.get(user_id)
        if not cart:
            return
        # compute qty to release
        existing = cart.items.get(product_id)
        if not existing:
            return
        to_release = existing.qty if qty is None else min(existing.qty, qty)
        cart.remove_item(product_id, qty)
        self._product_service.release(product_id, to_release)
        self.logger.log(f"{user_id} removed {product_id} qty={to_release} from cart")

    def view_cart(self, user_id: str):
        cart = self._carts.get(user_id)
        if not cart:
            return {}
        return {pid: {"name": it.name, "price": it.price, "qty": it.qty} for pid, it in cart.items.items()}

    def clear_cart(self, user_id: str):
        cart = self._carts.get(user_id)
        if not cart:
            return
        for pid, item in list(cart.items.items()):
            self._product_service.release(pid, item.qty)
        cart.clear()
