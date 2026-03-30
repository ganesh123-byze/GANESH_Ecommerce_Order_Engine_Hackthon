from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
# create product
r = client.post('/products', json={'name':'TestX','price':9.99,'stock':5})
print('POST', r.status_code, r.json())
pid = r.json().get('id')
# fetch product
r2 = client.get(f'/products/{pid}')
print('GET', r2.status_code, r2.json())
