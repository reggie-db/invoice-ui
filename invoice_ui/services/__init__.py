from __future__ import annotations

import os
from functools import lru_cache
from typing import Dict, Type

from invoice_ui.services.base import InvoiceService
from invoice_ui.services.demo import DemoInvoiceService

"""Service factory helpers for the invoice UI."""

_SERVICE_REGISTRY: Dict[str, Type[InvoiceService]] = {
    "demo": DemoInvoiceService,
}


@lru_cache(maxsize=1)
def get_invoice_service(kind: str | None = None) -> InvoiceService:
    """Return the configured invoice service implementation."""
    resolved_kind = (kind or os.getenv("INVOICE_UI_SERVICE", "demo")).lower()
    try:
        service_class = _SERVICE_REGISTRY[resolved_kind]
    except KeyError as exc:
        msg = f"Unknown invoice service kind: {resolved_kind}"
        raise ValueError(msg) from exc
    return service_class()

