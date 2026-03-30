from services.product_service import ProductService
from services.cart_service import CartService
from services.order_service import OrderService
from services.payment_service import PaymentService
from utils.logger import get_logger
from models.product import Product
from models.order import OrderItem
import threading
import time


class CLIController:
    def __init__(self):
        self.product_service = ProductService.instance()
        self.cart_service = CartService()
        self.order_service = OrderService()
        self.payment_service = self.order_service._payment
        self.logger = get_logger()

    def add_product(self):
        name = input("Product name: ")
        price = float(input("Price: "))
        stock = int(input("Stock: "))
        p = Product.create(name, price, stock)
        self.product_service.add_product(p)
        print(f"Added {p.id}")

    def view_products(self):
        for p in self.product_service.get_all():
            print(p)

    def add_to_cart(self):
        user = input("User id: ")
        pid = input("Product id: ")
        qty = int(input("Qty: "))
        ok = self.cart_service.add_to_cart(user, pid, qty)
        print("Added" if ok else "Failed to add (insufficient stock or invalid)")

    def remove_from_cart(self):
        user = input("User id: ")
        pid = input("Product id: ")
        qty = input("Qty (enter for full): ")
        qty = None if qty.strip() == "" else int(qty)
        self.cart_service.remove_from_cart(user, pid, qty)
        print("Removed")

    def view_cart(self):
        user = input("User id: ")
        print(self.cart_service.view_cart(user))

    def apply_coupon(self):
        print("Coupons: SAVE10, FLAT200")

    def place_order(self):
        user = input("User id: ")
        cart = self.cart_service._carts.get(user)
        if not cart or not cart.items:
            print("Cart empty")
            return
        coupon = input("Coupon (or enter): ") or None
        items = [OrderItem(product_id=i.product_id, name=i.name, price=i.price, qty=i.qty) for i in cart.items.values()]
        # build idempotency key
        idk = input("Idempotency key (optional): ") or None
        try:
            order = self.order_service.place_order(user, items, coupon, idk)
            # clear cart
            self.cart_service.clear_cart(user)
            print(f"Order placed: {order.id} total={order.total}")
        except Exception as e:
            print(f"Order failed: {e}")

    def cancel_order(self):
        oid = input("Order id: ")
        try:
            self.order_service.cancel_order(oid)
            print("Cancelled")
        except Exception as e:
            print(f"Cancel failed: {e}")

    def view_orders(self):
        for k, v in self.order_service.view_orders().items():
            print(k, v)

    def low_stock_alert(self):
        thr = input("Threshold (default 5): ")
        thr = int(thr) if thr.strip() else 5
        print(self.product_service.low_stock(thr))

    def return_product(self):
        oid = input("Order id: ")
        pid = input("Product id: ")
        qty = int(input("Qty: "))
        try:
            self.order_service.return_product(oid, pid, qty)
            print("Return processed")
        except Exception as e:
            print(f"Return failed: {e}")

    def simulate_concurrent(self):
        pid = input("Product id to stress: ")
        qty = int(input("Qty per user: "))
        users = int(input("Number of concurrent users: "))

        def worker(uid):
            ok = self.cart_service.add_to_cart(uid, pid, qty)
            if ok:
                items = [OrderItem(product_id=pid, name=self.product_service.get(pid).name, price=self.product_service.get(pid).price, qty=qty)]
                try:
                    self.order_service.place_order(uid, items, None, idempotency_key=f"sim-{uid}-{pid}")
                    print(f"User {uid} order success")
                except Exception as e:
                    print(f"User {uid} order failed: {e}")
            else:
                print(f"User {uid} could not reserve")

        threads = []
        for i in range(users):
            t = threading.Thread(target=worker, args=(f"user_{i+1}",))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

    def view_logs(self):
        for e in self.logger.all():
            print(e)

    def trigger_failure_mode(self):
        val = input("Enable failure mode? y/n: ")
        self.payment_service.set_failure_mode(val.lower() == 'y')
        print("Failure mode set")
