from __future__ import annotations

import base64
import os
from pathlib import Path

from dash import Dash, Input, Output, State, callback_context, dcc
from dash.exceptions import PreventUpdate
from reggie_tools import clients, configs

from invoice_ui.components.invoice_results import build_invoice_results
from invoice_ui.layout import build_layout
from invoice_ui.models.invoice import deserialize_invoice, serialize_invoice
from invoice_ui.services import get_invoice_service

"""Dash application entry point."""

PAGE_SIZE = 5
USE_LIVE = os.getenv("INVOICE_UI_USE_LIVE", "true").lower() in {"1", "true", "yes"}

_service = get_invoice_service("impl" if USE_LIVE else "demo")
_assets_path = Path(__file__).resolve().parents[2] / "assets"

app = Dash(__name__, title="Hardware Invoice Search", assets_folder=str(_assets_path))


def _decode_query_from_fragment(fragment: str | None) -> str:
    """Decode the search query from the URL fragment (format: search=base64)."""
    if not fragment:
        return ""
    try:
        # Parse format: search=base64encoded
        if fragment.startswith("search="):
            encoded_part = fragment[7:]  # Skip "search="
        else:
            # Fallback for old format (just base64)
            encoded_part = fragment

        # Add padding if needed (base64 requires length to be multiple of 4)
        padding = 4 - (len(encoded_part) % 4)
        if padding != 4:
            encoded_part += "=" * padding
        decoded_bytes = base64.urlsafe_b64decode(encoded_part)
        return decoded_bytes.decode("utf-8")
    except Exception:
        return ""


def _encode_query_to_fragment(query: str) -> str:
    """Encode the search query to a URL fragment (format: search=base64)."""
    if not query:
        return ""
    encoded_bytes = base64.urlsafe_b64encode(query.encode("utf-8"))
    encoded_str = encoded_bytes.decode("utf-8").rstrip("=")
    return f"search={encoded_str}"


# Initialize with query from URL fragment if present
_initial_query = ""
_initial_page = _service.list_invoices(
    query=_initial_query or None, page=1, page_size=PAGE_SIZE
)
app.layout = build_layout(_initial_page, _initial_query)


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
    prevent_initial_call=False,
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


# Initialize fragment handler and read initial fragment on page load
app.clientside_callback(
    """
    function(n) {
        if (typeof window === "undefined" || !window.__fragmentHandler) {
            return window.dash_clientside.no_update;
        }
        return window.__fragmentHandler.readFragment();
    }
    """,
    Output("search-query", "value"),
    Input("url", "pathname"),
    prevent_initial_call=False,
)

# Listen for fragment changes and update search query
app.clientside_callback(
    """
    function(hash, currentValue) {
        if (typeof window === "undefined" || !window.__fragmentHandler) {
            return window.dash_clientside.no_update;
        }
        
        const handler = window.__fragmentHandler;
        const currentHash = window.location.hash;
        
        // Check if this is an internal update we should ignore
        if (handler.isInternalUpdate(currentHash)) {
            return window.dash_clientside.no_update;
        }
        
        // External change - decode and update
        const decoded = handler.readFragment();
        
        // Only update if different from current value
        if (decoded !== (currentValue || '')) {
            return decoded;
        }
        
        return window.dash_clientside.no_update;
    }
    """,
    Output("search-query", "value", allow_duplicate=True),
    Input("url", "hash"),
    State("search-query", "value"),
    prevent_initial_call=True,
)

# Update fragment when search query changes
app.clientside_callback(
    """
    function(query) {
        if (typeof window === "undefined" || !window.__fragmentHandler) {
            return window.dash_clientside.no_update;
        }
        
        window.__fragmentHandler.updateFragment(query);
        return window.dash_clientside.no_update;
    }
    """,
    Output("url", "hash", allow_duplicate=True),
    Input("search-query", "value"),
    prevent_initial_call=True,
)


@app.callback(
    Output("download-file", "data"),
    Input({"type": "download-button", "index": "ALL"}, "n_clicks"),
    State("invoice-state", "data"),
    prevent_initial_call=True,
)
def handle_download(n_clicks_list: list[int | None], state: dict | None) -> dict | None:
    """Handle PDF download when download button is clicked."""
    if not state or not n_clicks_list:
        raise PreventUpdate

    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate

    # Find which button was clicked
    trigger_id = ctx.triggered[0]["prop_id"]
    if not trigger_id or trigger_id == ".":
        raise PreventUpdate

    # Extract invoice ID from the trigger
    try:
        import json

        trigger_dict = json.loads(trigger_id.replace(".n_clicks", ""))
        invoice_id = trigger_dict.get("index", "")
        if not invoice_id or not invoice_id.startswith("invoice-"):
            raise PreventUpdate

        # Extract invoice number from ID
        invoice_number = invoice_id.replace("invoice-", "")

        # Find the invoice in state
        invoices = _state_to_invoices(state)
        invoice = next(
            (inv for inv in invoices if inv.invoice.invoice_number == invoice_number),
            None,
        )

        if not invoice or not invoice.path:
            raise PreventUpdate

        # Download file using workspace client
        workspace = clients.workspace_client()
        file_path = invoice.path

        # Convert DBFS path to workspace path format
        # DBFS volumes like dbfs:/Volumes/... should be accessed as /Volumes/...
        workspace_path = file_path
        if file_path.startswith("dbfs:/"):
            workspace_path = file_path[5:]  # Remove "dbfs:" prefix

        # Read file from workspace using workspace client
        # The files API expects paths without dbfs: prefix for volumes
        file_response = workspace.files.download(workspace_path)
        file_content = file_response.contents

        # Extract filename from path
        filename = file_path.split("/")[-1] if "/" in file_path else "invoice.pdf"

        # Return file data for download
        return dcc.send_bytes(file_content, filename)

    except Exception as e:
        # Log error and prevent update
        import logging

        logging.error(f"Error downloading file: {e}")
        raise PreventUpdate


app.clientside_callback(
    """
    function tick(n, state) {
        if (typeof window === "undefined") {
            return 0;
        }
        
        // Stop polling if there's no more data
        if (!state || !state.has_more) {
            return state ? (state.scroll_token || 0) : 0;
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
    State("invoice-state", "data"),
)


def main() -> None:
    """Entrypoint used by uv via `uv run invoice_ui`."""
    if USE_LIVE:
        configs.get()
    app.run(debug=True, host="0.0.0.0", port=8050)


if __name__ == "__main__":
    main()
