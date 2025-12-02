from __future__ import annotations

import os
from functools import lru_cache
from typing import Callable, Dict

from reggie_core import logs

from invoice_ui.services.invoice_service import InvoiceService
from invoice_ui.services.invoice_service_demo import DemoInvoiceService
from invoice_ui.services.invoice_service_impl import InvoiceServiceImpl

"""Service factory helpers for the invoice UI."""

LOG = logs.logger(__file__)

_SERVICE_REGISTRY: Dict[str, Callable[[], InvoiceService]] = {
    "demo": lambda: DemoInvoiceService(),
    "impl": lambda: InvoiceServiceImpl(),
}


@lru_cache(maxsize=1)
def get_invoice_service(kind: str | None = None) -> InvoiceService:
    """Return the configured invoice service implementation."""
    resolved_kind = (kind or os.getenv("INVOICE_UI_SERVICE", "impl")).lower()
    LOG.info("get_invoice_service - kind:%s resolved_kind:%s", kind, resolved_kind)
    try:
        factory = _SERVICE_REGISTRY[resolved_kind]
    except KeyError as exc:
        msg = f"Unknown invoice service kind: {resolved_kind}"
        raise ValueError(msg) from exc
    return factory()
