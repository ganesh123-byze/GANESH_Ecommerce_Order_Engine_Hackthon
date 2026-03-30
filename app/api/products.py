from fastapi import APIRouter, Depends, HTTPException
from typing import List
from uuid import UUID

from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.product_service import get_product_service, ProductService

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.post("/", response_model=ProductRead)
def create_product(payload: ProductCreate, svc: ProductService = Depends(get_product_service)):
    p = svc.create(payload.name, payload.price, payload.quantity)
    return p


@router.get("/", response_model=List[ProductRead])
def list_products(svc: ProductService = Depends(get_product_service)):
    return svc.list()


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: UUID, svc: ProductService = Depends(get_product_service)):
    p = svc.get(product_id)
    if p is None:
        raise HTTPException(status_code=404, detail="product not found")
    return p


@router.put("/{product_id}", response_model=ProductRead)
def update_product(product_id: UUID, payload: ProductUpdate, svc: ProductService = Depends(get_product_service)):
    p = svc.update(product_id, name=payload.name, price=payload.price, quantity=payload.quantity)
    if p is None:
        raise HTTPException(status_code=404, detail="product not found")
    return p
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.product_service import get_product_service, ProductService

router = APIRouter()


def _get_svc() -> ProductService:
    return get_product_service()


@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(payload: ProductCreate, svc: ProductService = Depends(_get_svc)):
    rec = svc.create_product(payload)
    return ProductRead(id=rec.id, name=rec.name, price=rec.price, stock=rec.stock)


@router.get("/", response_model=List[ProductRead])
async def list_products(svc: ProductService = Depends(_get_svc)):
    items = svc.list_products()
    return [ProductRead(id=i.id, name=i.name, price=i.price, stock=i.stock) for i in items]


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: str, svc: ProductService = Depends(_get_svc)):
    rec = svc.get(product_id)
    if not rec:
        raise HTTPException(status_code=404, detail="product_not_found")
    return ProductRead(id=rec.id, name=rec.name, price=rec.price, stock=rec.stock)


@router.put("/{product_id}", response_model=ProductRead)
async def update_product(product_id: str, payload: ProductUpdate, svc: ProductService = Depends(_get_svc)):
    try:
        rec = svc.update(product_id, payload.dict(exclude_unset=True))
        return ProductRead(id=rec.id, name=rec.name, price=rec.price, stock=rec.stock)
    except KeyError:
        raise HTTPException(status_code=404, detail="product_not_found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
