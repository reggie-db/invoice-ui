from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from typing import Any, List, Mapping, Sequence

from invoice_ui.utils import parse_date

"""Dataclasses and helpers that describe invoice data made available to the UI."""


@dataclass(slots=True)
class Money:
    """Represents a monetary amount with an attached currency code."""

    currency: str
    value: float

    def format(self) -> str:
        """Return the monetary amount as a locale aware currency string."""
        return f"{self.currency} {self.value:,.2f}"


@dataclass(slots=True)
class Party:
    """Represents an entity involved with the invoice."""

    name: str
    address: Sequence[str]


@dataclass(slots=True)
class ShipTo(Party):
    """Adds the attention line that is present for shipping details."""

    attention: str


@dataclass(slots=True)
class InvoiceDetails:
    """Stores the identifying invoice metadata."""

    amount_due: Money
    invoice_number: str
    invoice_date: datetime
    purchase_order_number: str
    due_date: datetime | None
    sales_order_number: str
    terms: str

    def formatted_invoice_date(self) -> str:
        """Return the invoice date formatted for display."""
        return _format_date(self.invoice_date) if self.invoice_date else "N/A"

    def formatted_due_date(self) -> str:
        """Return the due date formatted for display or the N/A label."""
        if not self.due_date:
            return "N/A"
        return _format_date(self.due_date)


@dataclass(slots=True)
class LineItem:
    """Represents an individual line item on the invoice."""

    description: str
    serial_numbers: Sequence[str]
    line_number: str
    quantity_shipped: int
    manufacturer_part_number: str
    unit_price: float
    extended_price: float
    quantity_ordered: int


@dataclass(slots=True)
class Totals:
    """Aggregated monetary data for an invoice."""

    tax: float
    total: float
    currency: str
    subtotal: float
    shipping: float

    def as_money(self, value: float) -> str:
        """Format the provided numeric value as currency."""
        return f"{self.currency} {value:,.2f}"


@dataclass(slots=True)
class Invoice:
    """Primary dataclass for invoices."""

    line_items: Sequence[LineItem]
    ship_to: ShipTo
    invoice: InvoiceDetails
    buyer: Party
    seller: Party
    totals: Totals
    path: str = ""

    @property
    def dueDate(self) -> str:
        """Return the formatted due date for UI display."""
        return self.invoice.formatted_due_date()

    def searchable_terms(self) -> List[str]:
        """Return the terms that should be matched when filtering."""
        terms: List[str] = [
            self.invoice.invoice_number,
            self.invoice.purchase_order_number,
            self.invoice.sales_order_number,
            self.ship_to.name,
            self.ship_to.attention,
            self.buyer.name,
            self.seller.name,
        ]
        for line_item in self.line_items:
            terms.append(line_item.description)
            terms.append(line_item.manufacturer_part_number)
            terms.extend(line_item.serial_numbers)
        return [value.lower() for value in terms if value]


@dataclass(slots=True)
class InvoicePage:
    """Represents a single page of invoices."""

    items: Sequence[Invoice]
    total: int
    page: int
    page_size: int

    @property
    def has_more(self) -> bool:
        """Return True when additional pages are available."""
        # If we got fewer items than requested, we've reached the end
        if len(self.items) < self.page_size:
            return False
        # Otherwise check if there are more pages based on total
        return self.page * self.page_size < self.total


def _format_date(date: datetime | str | None) -> str:
    """Format a datetime object or date string into a readable presentation."""
    if not date:
        return "N/A"
    
    # Handle datetime objects
    if isinstance(date, datetime):
        return date.strftime("%b %d, %Y")
    
    # Handle string dates (fallback for backwards compatibility)
    if isinstance(date, str):
        try:
            parsed = datetime.fromisoformat(date)
            return parsed.strftime("%b %d, %Y")
        except (ValueError, TypeError):
            return "N/A"
    
    return "N/A"


def serialize_invoice(invoice: Invoice) -> dict:
    """Convert an Invoice dataclass into a JSON serializable dictionary."""
    data = asdict(invoice)
    # Convert datetime objects to ISO format strings for JSON serialization
    if "invoice" in data and "invoice_date" in data["invoice"]:
        if isinstance(data["invoice"]["invoice_date"], datetime):
            data["invoice"]["invoice_date"] = data["invoice"]["invoice_date"].isoformat()
    if "invoice" in data and "due_date" in data["invoice"]:
        if isinstance(data["invoice"]["due_date"], datetime):
            data["invoice"]["due_date"] = data["invoice"]["due_date"].isoformat()
    return data


def serialize_page(page: InvoicePage, query: str = "", scroll_token: int = 0) -> dict:
    """Serialize an InvoicePage to a JSON-compatible dictionary for dcc.Store."""
    return {
        "items": [serialize_invoice(inv) for inv in page.items],
        "total": page.total,
        "page": page.page,
        "page_size": page.page_size,
        "has_more": page.has_more,
        "query": query,
        "scroll_token": scroll_token,
    }


def deserialize_page(data: dict) -> InvoicePage:
    """Deserialize a dictionary back into an InvoicePage."""
    items = [deserialize_invoice(item) for item in data.get("items", [])]
    return InvoicePage(
        items=items,
        total=data.get("total", 0),
        page=data.get("page", 1),
        page_size=data.get("page_size", 10),
    )


def deserialize_invoice(payload: Mapping[str, Any]) -> Invoice:
    """Convert a dictionary structure back into an Invoice dataclass."""
    line_items = [LineItem(**item) for item in payload["line_items"]]
    ship_to = ShipTo(**payload["ship_to"])
    buyer = Party(**payload["buyer"])
    seller = Party(**payload["seller"])
    totals = Totals(**payload["totals"])
    
    # Parse date strings to datetime objects
    invoice_date_str = payload["invoice"]["invoice_date"]
    invoice_date = parse_date(invoice_date_str) if invoice_date_str else None
    if invoice_date is None:
        raise ValueError(f"Invalid invoice_date: {invoice_date_str}")
    
    due_date_str = payload["invoice"].get("due_date")
    due_date = parse_date(due_date_str) if due_date_str else None
    
    invoice_details = InvoiceDetails(
        amount_due=Money(**payload["invoice"]["amount_due"]),
        invoice_number=payload["invoice"]["invoice_number"],
        invoice_date=invoice_date,
        purchase_order_number=payload["invoice"]["purchase_order_number"],
        due_date=due_date,
        sales_order_number=payload["invoice"]["sales_order_number"],
        terms=payload["invoice"]["terms"],
    )
    return Invoice(
        line_items=line_items,
        ship_to=ship_to,
        invoice=invoice_details,
        buyer=buyer,
        seller=seller,
        totals=totals,
        path=payload.get("path", ""),
    )


def clone_invoice(invoice: Invoice, **overrides: Any) -> Invoice:
    """Return a shallow copy of an invoice with the provided overrides applied."""
    return replace(invoice, **overrides)
