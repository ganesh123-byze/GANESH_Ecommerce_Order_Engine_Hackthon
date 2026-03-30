from fastapi.testclient import TestClient
import api
import time


def run_extended_tests():
    client = TestClient(api.app)

    # create product
    r = client.post('/products', json={'name': 'XPhone', 'price': 5000.0, 'stock': 3})
    assert r.status_code == 200
    pid = r.json()['id']

    # add to cart
    r = client.post('/cart/add', json={'user_id': 'u1', 'product_id': pid, 'qty': 1})
    assert r.status_code == 200

    # view cart
    r = client.get('/cart/u1')
    assert r.status_code == 200 and pid in r.json()

    # place order with coupon
    r = client.post('/orders/place', json={'user_id': 'u1', 'coupon': 'SAVE10', 'idempotency_key': 'x-1'})
    assert r.status_code == 200
    oid = r.json()['order_id']

    # cancel order
    r = client.post(f'/orders/{oid}/cancel')
    assert r.status_code == 200

    # return product (make a new order first)
    r = client.post('/cart/add', json={'user_id': 'u2', 'product_id': pid, 'qty': 1})
    r = client.post('/orders/place', json={'user_id': 'u2', 'idempotency_key': 'x-2'})
    oid2 = r.json()['order_id']
    r = client.post(f'/orders/{oid2}/return', params={'product_id': pid, 'qty': 1})
    assert r.status_code == 200

    # simulate concurrent users
    r = client.post('/simulate/concurrent', params={'product_id': pid, 'qty': 1, 'users': 3})
    assert r.status_code == 200

    # check fraud flags (may be empty)
    r = client.get('/fraud/flags')
    assert r.status_code == 200

    # view logs
    r = client.get('/logs')
    assert r.status_code == 200

    print('Extended API tests passed')


if __name__ == '__main__':
    run_extended_tests()
