from fastapi.testclient import TestClient
import api


def run_tests():
    client = TestClient(api.app)

    # create product
    r = client.post('/products', json={'name': 'APIPhone', 'price': 12000.0, 'stock': 3})
    assert r.status_code == 200
    pid = r.json()['id']

    # list products
    r = client.get('/products')
    assert r.status_code == 200

    # add to cart
    r = client.post('/cart/add', json={'user_id': 'api_user', 'product_id': pid, 'qty': 1})
    assert r.status_code == 200

    # view cart
    r = client.get('/cart/api_user')
    assert r.status_code == 200

    # place order
    r = client.post('/orders/place', json={'user_id': 'api_user'})
    assert r.status_code == 200

    print('API smoke tests passed')


if __name__ == '__main__':
    run_tests()
