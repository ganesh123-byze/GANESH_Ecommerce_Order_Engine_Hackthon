import threading
import time

from models.product import Product
from models.order import OrderItem
from services.product_service import ProductService
from services.cart_service import CartService
from services.order_service import OrderService
from utils.logger import get_logger


def demo_concurrent_orders():
    logger = get_logger()
    ps = ProductService.instance()
    cs = CartService()
    osvc = OrderService()

    # create product with limited stock
    p = Product.create(name="DemoPhone", price=15000.0, stock=2)
    ps.add_product(p)

    pid = p.id

    results = {}

    def user_flow(user_id):
        try:
            # Each user tries to reserve 2 units
            ok = cs.add_to_cart(user_id, pid, 2, reserve_seconds=5)
            if not ok:
                results[user_id] = "reserve_failed"
                return
            items = [OrderItem(product_id=pid, name=p.name, price=p.price, qty=2)]
            order = osvc.place_order(user_id, items, coupon=None, idempotency_key=f"demo-{user_id}")
            results[user_id] = f"order_success:{order.id}"
        except Exception as e:
            results[user_id] = f"order_fail:{e}"

    threads = []
    for uid in ["user_A", "user_B"]:
        t = threading.Thread(target=user_flow, args=(uid,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    time.sleep(0.5)
    print("--- Demo Results ---")
    for k, v in results.items():
        print(k, v)

    print("Remaining stock:", ps.get(pid).stock)
    print("Orders:")
    for oid, meta in osvc.view_orders().items():
        print(oid, meta)

    print("Logs:")
    for e in logger.all():
        print(e)


if __name__ == '__main__':
    demo_concurrent_orders()
