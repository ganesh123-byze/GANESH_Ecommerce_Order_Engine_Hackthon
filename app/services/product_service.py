from threading import Lock
from typing import Dict, Optional
from uuid import uuid4, UUID
from dataclasses import dataclass


@dataclass
class Product:
    id: UUID
    name: str
    price: float
    quantity: int


class ProductService:
    def __init__(self):
        self._lock = Lock()
        self._products: Dict[UUID, Product] = {}

    def list(self):
        with self._lock:
            return list(self._products.values())

    def create(self, name: str, price: float, quantity: int) -> Product:
        with self._lock:
            pid = uuid4()
            p = Product(id=pid, name=name, price=price, quantity=quantity)
            self._products[pid] = p
            return p

    def get(self, pid: UUID) -> Optional[Product]:
        with self._lock:
            return self._products.get(pid)

    def update(self, pid: UUID, name: Optional[str] = None, price: Optional[float] = None, quantity: Optional[int] = None) -> Optional[Product]:
        with self._lock:
            p = self._products.get(pid)
            if p is None:
                return None
            if name is not None:
                p.name = name
            if price is not None:
                p.price = price
            if quantity is not None:
                if quantity < 0:
                    raise ValueError("quantity cannot be negative")
                p.quantity = quantity
            return p

    def has_stock(self, pid: UUID, qty: int) -> bool:
        with self._lock:
            p = self._products.get(pid)
            if p is None:
                return False
            return p.quantity >= qty

    def reserve(self, pid: UUID, qty: int) -> bool:
        """Atomically reserve qty units by decrementing available stock. Returns True if reserved."""
        if qty <= 0:
            return False
        with self._lock:
            p = self._products.get(pid)
            if p is None:
                return False
            if p.quantity < qty:
                return False
            p.quantity -= qty
            return True

    def release(self, pid: UUID, qty: int) -> bool:
        """Release previously reserved qty back into stock."""
        if qty <= 0:
            return False
        with self._lock:
            p = self._products.get(pid)
            if p is None:
                return False
            p.quantity += qty
            return True


_svc: Optional[ProductService] = None


def get_product_service() -> ProductService:
    global _svc
    if _svc is None:
        _svc = ProductService()
    return _svc
import threading
import uuid
from typing import Dict, List, Optional
from dataclasses import dataclass
from app.schemas.product import ProductCreate
from pydantic import BaseModel


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
