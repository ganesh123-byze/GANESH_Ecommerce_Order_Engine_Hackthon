from fastapi import APIRouter, Depends, HTTPException
from typing import List
from uuid import UUID

from app.schemas.order import PlaceOrderRequest, OrderRead, OrderItem
from app.services.order_service import get_order_service, OrderService
from app.services.cart_service import get_cart_service, CartService
from app.utils.audit_logger import get_audit_logger
from app.utils.event_bus import get_event_bus

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.post("/place")
def place_order(req: PlaceOrderRequest, order_svc: OrderService = Depends(get_order_service), cart_svc: CartService = Depends(get_cart_service)):
    # build items from cart
    cart = cart_svc.get_cart(req.user_id)
    if not cart:
        raise HTTPException(status_code=400, detail="cart empty")
    items = []
    for pid, qty in cart.items():
        # naive price lookup
        from app.services.product_service import get_product_service
        p = get_product_service().get(pid)
        if p is None:
            raise HTTPException(status_code=400, detail="product not found")
        items.append({"product_id": pid, "quantity": qty, "price": p.price})

    try:
        order = order_svc.place_order(req.user_id, items, coupon=req.coupon, idempotency_key=req.idempotency_key)
        cart_svc.clear_cart(req.user_id)
        # log via audit
        get_audit_logger().log(f"ORDER_PLACED id={order.id} user={req.user_id} total={order.total}")
        return {"order_id": order.id, "total": order.total}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[OrderRead])
def list_orders(order_svc: OrderService = Depends(get_order_service)):
    return order_svc.view_orders()


@router.post("/{order_id}/cancel")
def cancel_order(order_id: UUID, order_svc: OrderService = Depends(get_order_service)):
    try:
        order_svc.cancel_order(order_id)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/return")
def return_product(order_id: UUID, product_id: UUID, qty: int = 1, order_svc: OrderService = Depends(get_order_service)):
    try:
        order_svc.return_product(order_id, product_id, qty)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
