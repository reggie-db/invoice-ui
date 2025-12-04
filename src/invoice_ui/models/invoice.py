from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, List, Mapping, Sequence

from reggie_tools import genie

from invoice_ui.utils import format_currency, parse_date

"""Dataclasses and helpers that describe invoice data made available to the UI."""


@dataclass(slots=True)
class Money:
    """Represents a monetary amount with an attached currency code."""

    currency: str
    value: float

    def format(self) -> str:
        """Return the monetary amount as a locale aware currency string."""
        return format_currency(self.value, self.currency)


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
        return format_currency(value, self.currency)


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


def _format_date(date: datetime | None) -> str:
    """Format a datetime object into a readable presentation."""
    if not date:
        return "N/A"
    return date.strftime("%b %d, %Y")


def serialize_invoice(invoice: Invoice) -> dict:
    """Convert an Invoice dataclass into a JSON serializable dictionary."""
    data = asdict(invoice)
    # Convert datetime objects to ISO format strings for JSON serialization
    data["invoice"]["invoice_date"] = invoice.invoice.invoice_date.isoformat()
    if invoice.invoice.due_date:
        data["invoice"]["due_date"] = invoice.invoice.due_date.isoformat()
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
    inv = payload["invoice"]
    return Invoice(
        line_items=[LineItem(**item) for item in payload["line_items"]],
        ship_to=ShipTo(**payload["ship_to"]),
        buyer=Party(**payload["buyer"]),
        seller=Party(**payload["seller"]),
        totals=Totals(**payload["totals"]),
        invoice=InvoiceDetails(
            amount_due=Money(**inv["amount_due"]),
            invoice_number=inv["invoice_number"],
            invoice_date=parse_date(inv["invoice_date"]) or datetime.now(),
            purchase_order_number=inv["purchase_order_number"],
            due_date=parse_date(inv.get("due_date")),
            sales_order_number=inv["sales_order_number"],
            terms=inv["terms"],
        ),
        path=payload.get("path", ""),
    )


@dataclass
class GenieStatus:
    active: bool
    status: str | None
    message: str | None

    def __init__(self, genie_response: genie.GenieResponse | None):
        if genie_response is None:
            self.active = False
            self.status = None
            self.message = None
        else:
            self.active = True
            self.status = genie_response.status_display
            self.message = GenieStatus._message(genie_response)

    @staticmethod
    def _message(genie_response: genie.GenieResponse):
        if message := genie_response.message:
            content = message.content.strip() if message.content else None
            if content:
                return content
        return None
