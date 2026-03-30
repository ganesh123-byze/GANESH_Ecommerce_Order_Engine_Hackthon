from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class CartItem:
    product_id: str
    name: str
    price: float
    qty: int


@dataclass
class Cart:
    user_id: str
    items: Dict[str, CartItem] = field(default_factory=dict)

    def add_item(self, item: CartItem):
        if item.product_id in self.items:
            self.items[item.product_id].qty += item.qty
        else:
            self.items[item.product_id] = item

    def remove_item(self, product_id: str, qty: int = None):
        if product_id not in self.items:
            return
        if qty is None or self.items[product_id].qty <= qty:
            del self.items[product_id]
        else:
            self.items[product_id].qty -= qty

    def clear(self):
        self.items.clear()

    def total(self):
        return sum(i.price * i.qty for i in self.items.values())
