"""Internal canonical sales model."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class SalesTransaction:
    """Canonical representation of one raw Northstar sales transaction."""

    transaction_id: str
    sku: str
    quantity: int
    unit_price: Decimal
    transaction_timestamp: datetime
    channel: str

    def to_business_dict(self) -> dict[str, object]:
        """Return the stable business representation used for output and hashing."""
        return {
            "channel": self.channel,
            "quantity": self.quantity,
            "sku": self.sku,
            "transaction_id": self.transaction_id,
            "transaction_timestamp": self.transaction_timestamp.isoformat().replace("+00:00", "Z"),
            "unit_price": format(self.unit_price, "f"),
        }
