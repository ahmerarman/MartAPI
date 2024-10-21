from typing import Optional
from sqlmodel import SQLModel
from poservices.model.database import POTableBase, POLineItemBase

class POCreate(POTableBase):
    pass

class PORead(POTableBase):
    id: int

class POUpdate(SQLModel):
    VendorCode: int | None = None
    TotalOrderAmount: float | None = None
    TaxAmont: float | None = None
    GrandTotalAmount: float | None = None

class POUpdateComplete(POTableBase):
    pass


class POLineItemCreate(POLineItemBase):
    pass

class POLineItemRead(POLineItemBase):
    id: int

class POLineItemUpdate(SQLModel):
    PO_NO: int | None = None
    ProductID: int | None = None
    Quantity: int | None = None
    PurchasePrice: float | None = None

class POLineItemUpdateComplete(POLineItemBase):
    pass

class POReadWithLineItem(PORead):
    polineitem: Optional[list[POLineItemRead]] = []

class POLineItemReadWithPO(POLineItemRead):
    poinformations: Optional["PORead"] = None
