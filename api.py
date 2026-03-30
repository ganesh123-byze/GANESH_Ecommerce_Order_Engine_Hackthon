from fastapi import FastAPI, HTTPException
import threading
from pydantic import BaseModel
from typing import Optional, List

from services.product_service import ProductService
from services.cart_service import CartService
from services.order_service import OrderService
from services.payment_service import PaymentService
from models.product import Product
from models.order import OrderItem

app = FastAPI(title="E-Commerce Order Engine API")

# singletons
product_svc = ProductService.instance()
cart_svc = CartService()
order_svc = OrderService()
payment_svc = order_svc._payment

# initialize fraud service so it subscribes to events
from services.fraud_service import init_fraud_service
init_fraud_service()


class AddProductRequest(BaseModel):
    name: str
    price: float
    stock: int


class AddToCartRequest(BaseModel):
    user_id: str
    product_id: str
    qty: int


class PlaceOrderRequest(BaseModel):
    user_id: str
    coupon: Optional[str] = None
    idempotency_key: Optional[str] = None


@app.post("/products")
def add_product(req: AddProductRequest):
    p = Product.create(req.name, req.price, req.stock)
    product_svc.add_product(p)
    return {"id": p.id}


@app.get("/products")
def list_products():
    return product_svc.get_all()


@app.post("/cart/add")
def api_add_to_cart(req: AddToCartRequest):
    ok = cart_svc.add_to_cart(req.user_id, req.product_id, req.qty)
    if not ok:
        raise HTTPException(status_code=400, detail="Insufficient stock or invalid product")
    return {"ok": True}


@app.post("/cart/remove")
def api_remove_from_cart(req: AddToCartRequest):
    cart_svc.remove_from_cart(req.user_id, req.product_id, req.qty)
    return {"ok": True}


@app.get("/cart/{user_id}")
def api_view_cart(user_id: str):
    return cart_svc.view_cart(user_id)


@app.post("/orders/place")
def api_place_order(req: PlaceOrderRequest):
    cart = cart_svc._carts.get(req.user_id)
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart empty")
    items = [OrderItem(product_id=i.product_id, name=i.name, price=i.price, qty=i.qty) for i in cart.items.values()]
    try:
        order = order_svc.place_order(req.user_id, items, coupon=req.coupon, idempotency_key=req.idempotency_key)
        cart_svc.clear_cart(req.user_id)
        return {"order_id": order.id, "total": order.total}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/orders/{order_id}/return")
def api_return_product(order_id: str, product_id: str, qty: int):
    try:
        order_svc.return_product(order_id, product_id, qty)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/cart/clear")
def api_clear_cart(user_id: str):
    cart_svc.clear_cart(user_id)
    return {"ok": True}


@app.post("/simulate/concurrent")
def api_simulate_concurrent(product_id: str, qty: int, users: int = 2):
    """Simulate multiple users trying to add and place orders concurrently. Returns a summary."""
    results = {}

    def worker(uid):
        ok = cart_svc.add_to_cart(uid, product_id, qty)
        if not ok:
            results[uid] = 'reserve_failed'
            return
        items = [OrderItem(product_id=product_id, name=product_svc.get(product_id).name, price=product_svc.get(product_id).price, qty=qty)]
        try:
            order = order_svc.place_order(uid, items, idempotency_key=f"api-sim-{uid}-{product_id}")
            results[uid] = f"order_success:{order.id}"
        except Exception as e:
            results[uid] = f"order_failed:{e}"

    threads = []
    for i in range(users):
        uid = f"api_user_{i+1}"
        t = threading.Thread(target=worker, args=(uid,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    return results


@app.get("/fraud/flags")
def api_fraud_flags():
    from services.fraud_service import get_flags
    return get_flags()


@app.get("/orders")
def api_list_orders():
    return order_svc.view_orders()


@app.post("/orders/{order_id}/cancel")
def api_cancel_order(order_id: str):
    try:
        order_svc.cancel_order(order_id)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/low-stock")
def api_low_stock(threshold: int = 5):
    return product_svc.low_stock(threshold)


@app.post("/failure_mode")
def api_set_failure_mode(enable: bool):
    payment_svc.set_failure_mode(enable)
    return {"failure_mode": enable}


@app.get("/logs")
def api_logs():
    from utils.logger import get_logger

    logger = get_logger()
    return logger.all()
