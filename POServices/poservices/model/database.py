from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime, timezone


class POTableBase(SQLModel):
    VendorCode: int = Field(default=None, index=True)
    TotalOrderAmount: float = Field(default=None)
    TaxAmont: float = Field(default=None)
    GrandTotalAmount: float = Field(default=None)
    EnableEdit: bool = Field(default=True)
    CreatedDate: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class POTable(POTableBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True) # It is used as PO#
    poinformations: list["POLineItem"] = Relationship(back_populates="potable")

class POLineItemBase(SQLModel):
    PO_NO: int = Field(default=None, foreign_key="potable.id")
    ProductID: int = Field(default=None, index=True)
    Quantity: int = Field(default=None)
    PurchasePrice: float = Field(default=None)

class POLineItem(POLineItemBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    potable: Optional["POTable"] = Relationship(back_populates="poinformations")
