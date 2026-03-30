import threading
import uuid
from typing import Dict, List, Optional
from dataclasses import dataclass
from app.schemas.product import ProductCreate


@dataclass
class ProductRecord:
    id: str
    name: str
    price: float
    stock: int


class ProductService:
    """Thread-safe in-memory product service.

    Provides methods to create, update and query products. Uses per-product locks for safe stock
    manipulation.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._products: Dict[str, ProductRecord] = {}
        self._locks: Dict[str, threading.Lock] = {}

    def list_products(self) -> List[ProductRecord]:
        with self._lock:
            return list(self._products.values())

    def create_product(self, payload: ProductCreate) -> ProductRecord:
        with self._lock:
            pid = str(uuid.uuid4())
            if pid in self._products:
                # extremely unlikely, regenerate
                pid = str(uuid.uuid4())
            rec = ProductRecord(id=pid, name=payload.name, price=payload.price, stock=payload.stock)
            self._products[pid] = rec
            self._locks[pid] = threading.Lock()
            return rec

    def get(self, product_id: str) -> Optional[ProductRecord]:
        return self._products.get(product_id)

    def update(self, product_id: str, patch: dict) -> ProductRecord:
        if product_id not in self._products:
            raise KeyError("product_not_found")
        lock = self._locks[product_id]
        with lock:
            rec = self._products[product_id]
            name = patch.get("name", rec.name)
            price = patch.get("price", rec.price)
            stock = patch.get("stock", rec.stock)
            if stock < 0:
                raise ValueError("stock_cannot_be_negative")
            rec.name = name
            rec.price = price
            rec.stock = stock
            return rec

    def adjust_stock(self, product_id: str, delta: int):
        if product_id not in self._products:
            raise KeyError("product_not_found")
        lock = self._locks[product_id]
        with lock:
            rec = self._products[product_id]
            new = rec.stock + delta
            if new < 0:
                raise ValueError("insufficient_stock")
            rec.stock = new


# module-level singleton for dependency injection
_svc = ProductService()


def get_product_service() -> ProductService:
    return _svc
