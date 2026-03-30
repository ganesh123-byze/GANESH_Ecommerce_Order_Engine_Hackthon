from pydantic import BaseModel
from typing import Dict
from uuid import UUID


class CartItem(BaseModel):
    product_id: UUID
    quantity: int


class CartRead(BaseModel):
    user_id: str
    items: Dict[UUID, int]
