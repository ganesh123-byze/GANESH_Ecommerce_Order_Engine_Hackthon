import uuid
from dataclasses import dataclass, field


@dataclass
class Product:
    id: str
    name: str
    price: float
    stock: int = 0

    def to_dict(self):
        return {"id": self.id, "name": self.name, "price": self.price, "stock": self.stock}

    @staticmethod
    def create(name: str, price: float, stock: int):
        return Product(id=str(uuid.uuid4()), name=name, price=price, stock=stock)
