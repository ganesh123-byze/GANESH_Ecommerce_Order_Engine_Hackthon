from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)
    quantity: int = Field(..., ge=0)


class ProductUpdate(BaseModel):
    name: Optional[str]
    price: Optional[float]
    quantity: Optional[int]


class ProductRead(BaseModel):
    id: UUID
    name: str
    price: float
    quantity: int

    class Config:
        orm_mode = True
from pydantic import BaseModel, Field, conint, constr, PositiveFloat
from typing import Optional
from uuid import UUID


class ProductCreate(BaseModel):
    name: constr(min_length=1, max_length=200)
    price: PositiveFloat
    stock: conint(ge=0) = 0


class ProductUpdate(BaseModel):
    name: Optional[constr(min_length=1, max_length=200)]
    price: Optional[PositiveFloat]
    stock: Optional[conint(ge=0)]


class ProductRead(BaseModel):
    id: UUID
    name: str
    price: float
    stock: int

    class Config:
        orm_mode = True
