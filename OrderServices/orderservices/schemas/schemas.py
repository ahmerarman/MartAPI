from typing import Optional
from sqlmodel import SQLModel
from orderservices.model.database import OrderTableBase, OrderLineItemBase

class OrderCreate(OrderTableBase):
    pass

class OrderRead(OrderTableBase):
    id: int

class OrderUpdate(SQLModel):
    CustomerID: int | None = None
    PaymentRecordID: int | None = None
    TotalOrderAmount: float | None = None
    TaxAmont: float | None = None
    GrandTotalAmount: float | None = None
    EnableEdit: bool | None = None

class OrderUpdateComplete(OrderTableBase):
    pass

class OrderLineItemCreate(OrderLineItemBase):
    pass

class OrderLineItemRead(OrderLineItemBase):
    id: int

class OrderLineItemUpdate(SQLModel):
    OrderID: int | None = None
    ProductID: int | None = None
    Quantity: int | None = None
    SalePrice: float | None = None

class OrderLineItemUpdateComplete(OrderLineItemBase):
    pass

class OrderReadWithLineItem(OrderRead):
    orderlineitem: Optional[list[OrderLineItemRead]] = []

class OrderLineItemReadWithOrder(OrderLineItemRead):
    orderinformations: Optional["OrderRead"] = None
