"""
Service factory for the Invoice Search UI.

This module provides the get_invoice_service() factory function that returns
the appropriate InvoiceService implementation based on configuration.

Available Implementations:
- demo: In-memory service with static invoice data (no Databricks required)
- impl: Spark-backed service with Genie AI integration (requires Databricks)

The service is cached at the module level, so the same instance is reused
across all requests. Configure via INVOICE_UI_SERVICE environment variable.
"""

import os
from functools import cache, lru_cache
from typing import Callable, Dict

from reggie_core import logs

from invoice_ui.services.invoice_service import InvoiceService
from invoice_ui.services.invoice_service_demo import DemoInvoiceService
from invoice_ui.services.invoice_service_impl import InvoiceServiceImpl

LOG = logs.logger(__file__)

_SERVICE_REGISTRY: Dict[str, Callable[[], InvoiceService]] = {
    "demo": lambda: DemoInvoiceService(),
    "impl": lambda: InvoiceServiceImpl(),
}


@cache
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
