from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


from pydantic import BaseModel, Field, conint, constr, PositiveFloat
from typing import Optional


class ProductCreate(BaseModel):
    name: constr(min_length=1, max_length=200)
    price: PositiveFloat
    stock: conint(ge=0) = 0


class ProductUpdate(BaseModel):
    name: Optional[constr(min_length=1, max_length=200)]
    price: Optional[PositiveFloat]
    stock: Optional[conint(ge=0)]


class ProductRead(BaseModel):
    id: str
    name: str
    price: float
    stock: int

    class Config:
        orm_mode = True
