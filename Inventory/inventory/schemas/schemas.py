from sqlmodel import SQLModel
from inventory.model.database import InventoryBase

class InventoryCreate(InventoryBase):
    pass

class InventoryRead(InventoryBase):
    id: int

class InventoryUpdate(SQLModel):
    VendorID: int | None = None
    ProductID: int | None = None
    Enabled: bool | None = None
    PurchasePrice: float | None = None
    SalePrice: float | None = None
    Quantity: int | None = None
    Color: str | None = None
    Size: str | None = None

class InventoryUpdateComplete(InventoryBase):
    pass
