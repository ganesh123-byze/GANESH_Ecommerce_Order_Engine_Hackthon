from dataclasses import dataclass, field
from enum import Enum
from typing import List
import uuid


class OrderState(Enum):
    CREATED = "CREATED"
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class OrderItem:
    product_id: str
    name: str
    price: float
    qty: int


@dataclass
class Order:
    id: str
    user_id: str
    items: List[OrderItem]
    total: float
    state: OrderState = OrderState.CREATED
    coupon: str = None
    metadata: dict = field(default_factory=dict)

    @staticmethod
    def create(user_id: str, items: List[OrderItem], total: float, coupon: str = None):
        return Order(id=str(uuid.uuid4()), user_id=user_id, items=items, total=total, coupon=coupon)
