from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime, timezone


class OrderTableBase(SQLModel):
    CustomerID: int = Field(default=None, index=True)
    PaymentRecordID: Optional[int] = Field(default=None)
    TotalOrderAmount: float = Field(default=None)
    TaxAmont: float = Field(default=None)
    GrandTotalAmount: float = Field(default=None)
    EnableEdit: bool = Field(default=True)
    CreatedDate: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OrderTable(OrderTableBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    orderinformations: list["OrderLineItem"] = Relationship(back_populates="ordertable")

class OrderLineItemBase(SQLModel):
    OrderID: int = Field(default=None, foreign_key="ordertable.id")
    ProductID: int = Field(default=None, index=True)
    Quantity: int = Field(default=None)
    SalePrice: float = Field(default=None)

class OrderLineItem(OrderLineItemBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ordertable: Optional["OrderTable"] = Relationship(back_populates="orderinformations")
