from fastapi import APIRouter, Depends, HTTPException
from typing import Dict

from app.services.cart_service import get_cart_service, CartService
from app.schemas.cart import CartItem, CartRead

router = APIRouter(prefix="/api/v1/carts", tags=["carts"])


@router.post("/{user_id}/items")
def add_item(user_id: str, item: CartItem, svc: CartService = Depends(get_cart_service)):
    ok = svc.add_item(user_id, item.product_id, item.quantity)
    if not ok:
        raise HTTPException(status_code=400, detail="unable to add item (insufficient stock or invalid)")
    return {"ok": True}


@router.delete("/{user_id}/items/{product_id}")
def remove_item(user_id: str, product_id: str, svc: CartService = Depends(get_cart_service)):
    from uuid import UUID as _UUID
    try:
        pid = _UUID(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid product id")
    ok = svc.remove_item(user_id, pid)
    if not ok:
        raise HTTPException(status_code=404, detail="item not in cart")
    return {"ok": True}


@router.put("/{user_id}/items")
def update_item(user_id: str, item: CartItem, svc: CartService = Depends(get_cart_service)):
    ok = svc.update_quantity(user_id, item.product_id, item.quantity)
    if not ok:
        raise HTTPException(status_code=400, detail="unable to update item (insufficient stock or invalid)")
    return {"ok": True}


@router.get("/{user_id}", response_model=CartRead)
def view_cart(user_id: str, svc: CartService = Depends(get_cart_service)):
    items = svc.get_cart(user_id)
    return {"user_id": user_id, "items": items}
