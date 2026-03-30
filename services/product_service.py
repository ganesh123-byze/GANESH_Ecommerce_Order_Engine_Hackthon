import threading
import time
from typing import Dict, Optional
from models.product import Product
from utils.logger import get_logger


class ProductService:
    """Singleton service managing products and stock with locks and reservations."""

    _instance = None
    _inst_lock = threading.Lock()

    def __init__(self):
        self._products: Dict[str, Product] = {}
        self._stock_locks: Dict[str, threading.Lock] = {}
        # reserved: product_id -> reserved_qty
        self._reserved: Dict[str, int] = {}
        self._global_lock = threading.Lock()
        self.logger = get_logger()

    @classmethod
    def instance(cls):
        with cls._inst_lock:
            if cls._instance is None:
                cls._instance = ProductService()
            return cls._instance

    def add_product(self, product: Product):
        with self._global_lock:
            if product.id in self._products:
                raise ValueError("Product ID already exists")
            self._products[product.id] = product
            self._stock_locks[product.id] = threading.Lock()
            self._reserved[product.id] = 0
        self.logger.log(f"PRODUCT_ADD user=SYSTEM id={product.id} name={product.name} stock={product.stock}")

    def get_all(self):
        with self._global_lock:
            return [p.to_dict() for p in self._products.values()]

    def get(self, product_id: str) -> Optional[Product]:
        return self._products.get(product_id)

    def update_stock(self, product_id: str, delta: int):
        # delta can be negative
        if product_id not in self._products:
            raise KeyError("Unknown product")
        lock = self._stock_locks[product_id]
        with lock:
            new_stock = self._products[product_id].stock + delta
            if new_stock < 0:
                raise ValueError("Stock cannot be negative")
            self._products[product_id].stock = new_stock
        self.logger.log(f"STOCK_UPDATE product={product_id} delta={delta} new={self._products[product_id].stock}")

    def reserve(self, product_id: str, qty: int) -> bool:
        """Try to reserve qty; return True if reserved."""
        if product_id not in self._products:
            return False
        lock = self._stock_locks[product_id]
        with lock:
            avail = self._products[product_id].stock - self._reserved.get(product_id, 0)
            if qty <= 0:
                return False
            if avail >= qty:
                self._reserved[product_id] = self._reserved.get(product_id, 0) + qty
                self.logger.log(f"RESERVE product={product_id} qty={qty} reserved={self._reserved[product_id]}")
                return True
            else:
                return False

    def get_reserved(self, product_id: str) -> int:
        """Return currently reserved qty for a product."""
        return self._reserved.get(product_id, 0)

    def has_commitable(self, product_id: str, qty: int) -> bool:
        """Check if the reserved qty and available stock make a commit possible.

        Ensures reserved >= qty and stock >= qty.
        """
        if product_id not in self._products:
            return False
        # locked read for safety
        lock = self._stock_locks[product_id]
        with lock:
            reserved = self._reserved.get(product_id, 0)
            stock = self._products[product_id].stock
            return reserved >= qty and stock >= qty

    def release(self, product_id: str, qty: int):
        if product_id not in self._products:
            return
        lock = self._stock_locks[product_id]
        with lock:
            self._reserved[product_id] = max(0, self._reserved.get(product_id, 0) - qty)
        self.logger.log(f"RELEASE product={product_id} qty={qty} reserved={self._reserved[product_id]}")

    def commit_reservation(self, product_id: str, qty: int):
        # remove reserved and decrement stock
        lock = self._stock_locks[product_id]
        with lock:
            reserved = self._reserved.get(product_id, 0)
            if reserved < qty:
                raise ValueError("Not enough reserved stock to commit")
            self._reserved[product_id] = reserved - qty
            if self._products[product_id].stock < qty:
                raise ValueError("Insufficient stock on commit")
            self._products[product_id].stock -= qty
        self.logger.log(f"COMMIT product={product_id} qty={qty} new_stock={self._products[product_id].stock}")

    def low_stock(self, threshold: int = 5):
        with self._global_lock:
            return [p.to_dict() for p in self._products.values() if p.stock <= threshold]
