from pydantic import BaseModel
from typing import List, Optional, Dict
from uuid import UUID


class OrderItem(BaseModel):
    product_id: UUID
    quantity: int
    price: float


class PlaceOrderRequest(BaseModel):
    user_id: str
    coupon: Optional[str] = None
    idempotency_key: Optional[str] = None


class OrderRead(BaseModel):
    order_id: UUID
    user_id: str
    items: List[OrderItem]
    total: float
    state: str
