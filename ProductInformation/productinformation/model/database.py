from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime, timezone


class ProductCatagoryBase(SQLModel):
    CatagoryName: str = Field(default=None, index=True, max_length=50)
    BaseCatagory: Optional[int] = Field(default=None)
    Description: Optional[str] = Field(default=None, max_length=200)

class ProductCatagory(ProductCatagoryBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    productinformations: list["ProductInformation"] = Relationship(back_populates="productcatagory")

class ProductInformationBase(SQLModel):
    ProductName: str = Field(default=None, index=True, max_length=50)
    ProductDescription: Optional[str] = Field(default=None, index=True, max_length=100)
    Enabled: bool = Field(default=True)
    CreatedDate: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ImageURL: Optional[str] = Field(default=None, max_length=255)
    Catagory_id: Optional[int] = Field(default=None, foreign_key="productcatagory.id")

class ProductInformation(ProductInformationBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    productcatagory: Optional["ProductCatagory"] = Relationship(back_populates="productinformations")
