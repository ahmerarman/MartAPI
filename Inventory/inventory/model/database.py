from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime, timezone

class InventoryBase(SQLModel):
    VendorID: int = Field(default=None, index=True)
    ProductID: int = Field(default=None, index=True)
    Enabled: bool = True
    PurchasePrice: float = Field(default=None)
    SalePrice: float = Field(default=None)
    Quantity: int = Field(default=None)
    Color: Optional[str] = Field(default=None, max_length=20)
    Size: Optional[str] = Field(default=None, max_length=20)
    CreatedDate: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Inventory(InventoryBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
