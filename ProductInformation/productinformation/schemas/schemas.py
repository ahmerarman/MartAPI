from typing import Optional
from sqlmodel import SQLModel
from productinformation.model.database import ProductInformationBase, ProductCatagoryBase

class CatagoryCreate(ProductCatagoryBase):
    pass

class CatagoryRead(ProductCatagoryBase):
    id: int

class CatagoryUpdate(SQLModel):
    CatagoryName: str | None = None
    BaseCatagory: int | None = None
    Description: str | None = None

class CatagoryUpdateComplete(ProductCatagoryBase):
    pass

class ProductCreate(ProductInformationBase):
    pass

class ProductRead(ProductInformationBase):
    id: int

class ProductUpdate(SQLModel):
    ProductName: str | None = None
    ProductDescription: str | None = None
    Enabled: bool | None = None
    ImageURL: str | None = None
    Catagory_id: int | None = None

class ProductUpdateComplete(ProductInformationBase):
    pass

class ProductReadWithCatagory(ProductRead):
    productcatagory: Optional["CatagoryRead"] = None

class CatagoryReadWithProduct(CatagoryRead):
    productinformations: Optional[list[ProductRead]] = []
