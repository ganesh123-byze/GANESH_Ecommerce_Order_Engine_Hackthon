import threading
import time
import random

# make payment randomness deterministic for feature tests
random.seed(1)

from models.product import Product
from models.order import OrderItem
from services.product_service import ProductService
from services.cart_service import CartService
from services.order_service import OrderService
from services.payment_service import PaymentService
from utils.events import get_event_bus
from utils.logger import get_logger


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_product_management():
    ps = ProductService.instance()
    # add product
    p = Product.create('TestProd', 100.0, 5)
    ps.add_product(p)
    # unique ID enforcement: adding same id object should raise
    try:
        ps.add_product(p)
        raise AssertionError('Duplicate product id allowed')
    except ValueError:
        pass

    # prevent negative stock
    try:
        ps.update_stock(p.id, -100)
        raise AssertionError('Allowed negative stock')
    except ValueError:
        pass


def test_cart_reservation_and_release():
    ps = ProductService.instance()
    cs = CartService()
    p = Product.create('CartProd', 50.0, 5)
    ps.add_product(p)
    ok = cs.add_to_cart('u1', p.id, 3, reserve_seconds=2)
    assert_true(ok, 'Failed to reserve')
    # reserved should be 3
    assert_true(ps._reserved[p.id] >= 3, 'Reserved count incorrect')
    # remove and check release
    cs.remove_from_cart('u1', p.id, 2)
    assert_true(ps._reserved[p.id] >= 1, 'Release on remove incorrect')


def test_reservation_expiry():
    ps = ProductService.instance()
    cs = CartService()
    p = Product.create('ExpiryProd', 20.0, 2)
    ps.add_product(p)
    ok = cs.add_to_cart('u_exp', p.id, 1, reserve_seconds=1)
    assert_true(ok, 'reserve failed')
    time.sleep(1.6)
    # reservation should be released and cart empty
    assert_true(ps._reserved.get(p.id, 0) == 0, 'Expiry did not release reservation')
    assert_true('u_exp' not in cs._carts or p.id not in cs._carts['u_exp'].items, 'Cart not cleared after expiry')


def test_concurrency_only_one_succeeds():
    ps = ProductService.instance()
    cs = CartService()
    osvc = OrderService()
    # ensure payment not in injected failure mode for this test
    osvc._payment.set_failure_mode(False)
    # force payment to succeed for deterministic test
    osvc._payment.charge = lambda user_id, amount: True
    p = Product.create('ConcProd', 100.0, 1)
    ps.add_product(p)

    results = {}

    def flow(uid):
        ok = cs.add_to_cart(uid, p.id, 1)
        if not ok:
            results[uid] = 'reserve_failed'
            return
        try:
            order = osvc.place_order(uid, [OrderItem(product_id=p.id, name=p.name, price=p.price, qty=1)], idempotency_key=f'conc-{uid}')
            results[uid] = 'order_success'
        except Exception as e:
            results[uid] = f'order_fail:{e}'

    t1 = threading.Thread(target=flow, args=('A',))
    t2 = threading.Thread(target=flow, args=('B',))
    t1.start(); t2.start(); t1.join(); t2.join()

    successes = [v for v in results.values() if v == 'order_success']
    assert_true(len(successes) == 1, f'Expected 1 success, got {len(successes)}')


def test_payment_failure_rollback():
    ps = ProductService.instance()
    cs = CartService()
    osvc = OrderService()
    pay = osvc._payment
    p = Product.create('FailProd', 200.0, 2)
    ps.add_product(p)
    # enable failure mode
    pay.set_failure_mode(True)
    ok = cs.add_to_cart('fuser', p.id, 1)
    assert_true(ok, 'reserve failed')
    try:
        osvc.place_order('fuser', [OrderItem(product_id=p.id, name=p.name, price=p.price, qty=1)], idempotency_key='fail-1')
        raise AssertionError('Payment succeeded unexpectedly')
    except RuntimeError:
        # expected; ensure reservation released
        assert_true(ps._reserved.get(p.id, 0) == 0, 'Reservation not released after payment failure')
    finally:
        pay.set_failure_mode(False)


def test_discounts_and_coupons():
    ps = ProductService.instance()
    cs = CartService()
    osvc = OrderService()
    osvc._payment.set_failure_mode(False)
    osvc._payment.charge = lambda user_id, amount: True
    p = Product.create('DiscProd', 400.0, 10)
    ps.add_product(p)
    cs.add_to_cart('duser', p.id, 3)
    items = [OrderItem(product_id=p.id, name=p.name, price=p.price, qty=3)]
    order = osvc.place_order('duser', items, coupon='SAVE10', idempotency_key='disc-1')
    # subtotal = 1200, 10% rule + coupon 10% => 20% total discount => total 960
    assert_true(abs(order.total - 960.0) < 0.01, f'Discount calculation incorrect: {order.total}')


def test_low_stock_and_cancel_and_return():
    ps = ProductService.instance()
    cs = CartService()
    osvc = OrderService()
    osvc._payment.set_failure_mode(False)
    osvc._payment.charge = lambda user_id, amount: True
    p = Product.create('LowProd', 50.0, 2)
    ps.add_product(p)
    # low stock threshold
    lows = ps.low_stock(2)
    assert_true(any(x['id'] == p.id for x in lows), 'Low stock not reported')

    # create order and then cancel
    cs.add_to_cart('cuser', p.id, 1)
    order = osvc.place_order('cuser', [OrderItem(product_id=p.id, name=p.name, price=p.price, qty=1)], idempotency_key='cancel-1')
    pre_stock = ps.get(p.id).stock
    osvc.cancel_order(order.id)
    assert_true(ps.get(p.id).stock >= pre_stock + 1 - 0, 'Stock not restored on cancel')

    # returns
    cs.add_to_cart('ruser', p.id, 1)
    order2 = osvc.place_order('ruser', [OrderItem(product_id=p.id, name=p.name, price=p.price, qty=1)], idempotency_key='return-1')
    total_before = order2.total
    osvc.return_product(order2.id, p.id, 1)
    assert_true(order2.total < total_before, 'Return did not reduce total')


def test_events_sequential():
    bus = get_event_bus()
    seq = []

    def h1(payload):
        seq.append('h1')

    def h2(payload):
        seq.append('h2')

    bus.subscribe('TEST_EVT', h1)
    bus.subscribe('TEST_EVT', h2)
    bus.publish('TEST_EVT', {})
    assert_true(seq == ['h1', 'h2'], 'Event handlers not executed sequentially')


def test_idempotency():
    ps = ProductService.instance()
    cs = CartService()
    osvc = OrderService()
    osvc._payment.set_failure_mode(False)
    osvc._payment.charge = lambda user_id, amount: True
    p = Product.create('IdemProd', 30.0, 5)
    ps.add_product(p)
    cs.add_to_cart('iuser', p.id, 1)
    items = [OrderItem(product_id=p.id, name=p.name, price=p.price, qty=1)]
    o = osvc.place_order('iuser', items, idempotency_key='idem-1')
    try:
        osvc.place_order('iuser', items, idempotency_key='idem-1')
        raise AssertionError('Idempotent duplicate allowed')
    except RuntimeError:
        pass


def run_all():
    tests = [
        test_product_management,
        test_cart_reservation_and_release,
        test_reservation_expiry,
        test_concurrency_only_one_succeeds,
        test_payment_failure_rollback,
        test_discounts_and_coupons,
        test_low_stock_and_cancel_and_return,
        test_events_sequential,
        test_idempotency,
    ]

    for t in tests:
        name = t.__name__
        try:
            t()
            print(f"[PASS] {name}")
        except AssertionError as e:
            print(f"[FAIL] {name}: {e}")
            raise
        except Exception as e:
            print(f"[ERROR] {name}: {e}")
            raise

    print('All feature tests passed')


if __name__ == '__main__':
    run_all()
