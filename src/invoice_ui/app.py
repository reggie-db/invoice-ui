from __future__ import annotations

import os
from pathlib import Path

from dash import Dash, Input, Output, State, callback_context
from dash.exceptions import PreventUpdate
from reggie_tools import configs

from invoice_ui.components.invoice_results import build_invoice_results
from invoice_ui.layout import build_layout
from invoice_ui.models.invoice import deserialize_invoice, serialize_invoice
from invoice_ui.services import get_invoice_service

"""Dash application entry point."""

PAGE_SIZE = 5
USE_LIVE = os.getenv("INVOICE_UI_USE_LIVE", "true").lower() in {"1", "true", "yes"}

_service = get_invoice_service("impl" if USE_LIVE else "demo")
_initial_page = _service.list_invoices(page=1, page_size=PAGE_SIZE)
_assets_path = Path(__file__).resolve().parents[2] / "assets"

app = Dash(__name__, title="Hardware Invoice Search", assets_folder=str(_assets_path))
app.layout = build_layout(_initial_page)


def _page_to_state(page, query: str, scroll_token: int) -> dict:
    """Serialize a page response into a structure suitable for dcc.Store."""
    return {
        "query": query,
        "page": page.page,
        "page_size": page.page_size,
        "total": page.total,
        "items": [serialize_invoice(invoice) for invoice in page.items],
        "has_more": page.has_more,
        "scroll_token": scroll_token,
    }


def _state_to_invoices(state: dict) -> list:
    """Convert stored invoice dictionaries back into dataclasses."""
    return [deserialize_invoice(payload) for payload in state.get("items", [])]


@app.callback(
    Output("invoice-state", "data"),
    Input("search-query", "value"),
    Input("scroll-trigger", "data"),
    State("invoice-state", "data"),
    prevent_initial_call=True,
)
def update_invoice_state(
    query: str | None,
    scroll_counter: int | None,
    state: dict | None,
) -> dict:
    """Handle both filter changes and scroll-based lazy loading."""
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    if trigger == "search-query":
        query_text = (query or "").strip()
        page_size = (state or {}).get("page_size", PAGE_SIZE)
        page = _service.list_invoices(
            query=query_text or None,
            page=1,
            page_size=page_size,
        )
        return _page_to_state(page, query_text, scroll_counter or 0)

    if trigger == "scroll-trigger":
        if not state or not state.get("has_more"):
            raise PreventUpdate
        if scroll_counter is None or scroll_counter == state.get("scroll_token"):
            raise PreventUpdate

        next_page = state.get("page", 1) + 1
        page_size = state.get("page_size", PAGE_SIZE)
        query_text = state.get("query") or ""
        page = _service.list_invoices(
            query=query_text or None,
            page=next_page,
            page_size=page_size,
        )
        combined_items = state.get("items", []) + [
            serialize_invoice(invoice) for invoice in page.items
        ]
        return {
            **state,
            "items": combined_items,
            "page": page.page,
            "page_size": page.page_size,
            "total": page.total,
            "has_more": page.has_more,
            "scroll_token": scroll_counter,
        }

    raise PreventUpdate


@app.callback(Output("results-container", "children"), Input("invoice-state", "data"))
def render_results(state: dict) -> object:
    """Render invoice results whenever the backing store changes."""
    if not state:
        raise PreventUpdate
    invoices = _state_to_invoices(state)
    query = state.get("query") or ""
    return build_invoice_results(invoices, query, state.get("has_more", False))


app.clientside_callback(
    """
    function tick(n) {
        if (typeof window === "undefined") {
            return 0;
        }
        const doc = document.documentElement || document.body;
        const scrollTop = window.pageYOffset || doc.scrollTop || 0;
        const innerHeight = window.innerHeight || doc.clientHeight || 0;
        const scrollHeight = doc.scrollHeight || document.body.scrollHeight || 0;
        const threshold = 200;
        const nearBottom = scrollTop + innerHeight >= scrollHeight - threshold;

        window.__invoiceScrollCount = window.__invoiceScrollCount || 0;
        window.__invoiceScrollPending = window.__invoiceScrollPending || false;

        if (nearBottom) {
            if (!window.__invoiceScrollPending) {
                window.__invoiceScrollPending = true;
                window.__invoiceScrollCount += 1;
            }
        } else {
            window.__invoiceScrollPending = false;
        }

        return window.__invoiceScrollCount;
    }
    """,
    Output("scroll-trigger", "data"),
    Input("scroll-poller", "n_intervals"),
)


def main() -> None:
    """Entrypoint used by uv via `uv run invoice_ui`."""
    if USE_LIVE:
        configs.get()
    app.run(debug=True, host="0.0.0.0", port=8050)


if __name__ == "__main__":
    main()
