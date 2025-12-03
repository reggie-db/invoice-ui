from __future__ import annotations

import os
from pathlib import Path

from dash import ALL, Dash, Input, Output, State, callback_context, dcc
from dash.exceptions import PreventUpdate
from reggie_core import logs
from reggie_tools import clients, configs

from invoice_ui.components.invoice_results import build_invoice_results
from invoice_ui.layout import build_layout
from invoice_ui.models.invoice import (
    InvoicePage,
    deserialize_page,
    serialize_invoice,
    serialize_page,
)
from invoice_ui.services import get_invoice_service

"""Dash application entry point for the invoice search UI."""

LOG = logs.logger(__file__)

PAGE_SIZE = 1
USE_LIVE = os.getenv("INVOICE_UI_USE_LIVE", "true").lower() in {"1", "true", "yes"}

_service = get_invoice_service("impl" if USE_LIVE else "demo")
_assets_path = Path(__file__).resolve().parents[2] / "assets"

app = Dash(__name__, title="Hardware Invoice Search", assets_folder=str(_assets_path))


# Initialize with query from URL fragment if present
_initial_query = ""
_initial_page = _service.list_invoices(
    query=_initial_query or None, page=1, page_size=PAGE_SIZE
)
app.layout = build_layout(_initial_page, _initial_query)


def _state_to_page(state: dict) -> InvoicePage:
    """Convert stored state back into an InvoicePage."""
    return deserialize_page(state)


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
        return serialize_page(page, query_text, scroll_counter or 0)

    if trigger == "scroll-trigger":
        if not state or not state.get("has_more"):
            raise PreventUpdate
        if scroll_counter is None or scroll_counter == state.get("scroll_token"):
            raise PreventUpdate

        next_page_num = state.get("page", 1) + 1
        page_size = state.get("page_size", PAGE_SIZE)
        query_text = state.get("query") or ""
        new_page = _service.list_invoices(
            query=query_text or None,
            page=next_page_num,
            page_size=page_size,
        )
        # Combine items from previous state with new page items
        combined_items = state.get("items", []) + [
            serialize_invoice(invoice) for invoice in new_page.items
        ]
        return {
            "items": combined_items,
            "total": new_page.total,
            "page": new_page.page,
            "page_size": new_page.page_size,
            "has_more": new_page.has_more,
            "query": query_text,
            "scroll_token": scroll_counter,
        }

    raise PreventUpdate


@app.callback(Output("results-container", "children"), Input("invoice-state", "data"))
def render_results(state: dict) -> object:
    """Render invoice results whenever the backing store changes."""
    if not state:
        raise PreventUpdate
    page = _state_to_page(state)
    query = state.get("query") or ""
    has_more = state.get("has_more", False)
    return build_invoice_results(page, query, has_more)


# Initialize hash router and read initial hash on page load
# The hash-router-handler.js will handle routing and update search-query via dash.set_props
# This callback ensures Dash is aware of the initial value
app.clientside_callback(
    """
    function(n) {
        if (typeof window === "undefined") {
            return window.dash_clientside.no_update;
        }
        
        // Read current hash and decode if present
        const hash = window.location.hash.substring(1);
        if (hash && hash.startsWith('search/')) {
            const encoded = hash.substring(7);
            try {
                const padding = 4 - (encoded.length % 4);
                const padded = padding !== 4 ? encoded + '='.repeat(padding) : encoded;
                return atob(padded);
            } catch (e) {
                return '';
            }
        }
        
        return '';
    }
    """,
    Output("search-query", "value"),
    Input("url", "pathname"),
    prevent_initial_call=False,
)

# Listen for hash changes - hash-router handles this, but we sync with Dash
app.clientside_callback(
    """
    function(hash) {
        if (typeof window === "undefined") {
            return window.dash_clientside.no_update;
        }
        
        // Hash router will handle the routing and call updateSearchInput
        // But we also decode here to ensure Dash state is updated
        const currentHash = window.location.hash.substring(1);
        let decoded = '';
        
        if (currentHash && currentHash.startsWith('search/')) {
            const encoded = currentHash.substring(7);
            try {
                const padding = 4 - (encoded.length % 4);
                const padded = padding !== 4 ? encoded + '='.repeat(padding) : encoded;
                decoded = atob(padded);
            } catch (e) {
                decoded = '';
            }
        }
        
        return decoded;
    }
    """,
    Output("search-query", "value", allow_duplicate=True),
    Input("url", "hash"),
    prevent_initial_call=True,
)

# Update hash when search query changes
app.clientside_callback(
    """
    function(query) {
        if (typeof window === "undefined") {
            return window.dash_clientside.no_update;
        }
        
        if (window.__updateHashFromQuery) {
            window.__updateHashFromQuery(query || '');
        }
        
        return window.dash_clientside.no_update;
    }
    """,
    Output("url", "hash", allow_duplicate=True),
    Input("search-query", "value"),
    prevent_initial_call=True,
)


@app.callback(
    Output("download-file", "data"),
    Input({"type": "download-button", "index": ALL}, "n_clicks"),
    State("invoice-state", "data"),
    prevent_initial_call=True,
)
def handle_download(n_clicks_list: list[int | None], state: dict | None) -> dict | None:
    """Handle PDF download when download button is clicked."""
    import json

    ctx = callback_context

    # Check if any button was actually clicked (not just initial render)
    if not n_clicks_list or all(n is None or n == 0 for n in n_clicks_list):
        raise PreventUpdate

    if not ctx.triggered or not state:
        raise PreventUpdate

    # Get the triggered button's ID from context
    triggered_id = ctx.triggered_id

    # triggered_id should be a dict like {"type": "download-button", "index": "invoice-123"}
    if not triggered_id:
        # Fallback: parse from prop_id
        prop_id = ctx.triggered[0].get("prop_id", "")
        if ".n_clicks" in prop_id:
            id_str = prop_id.replace(".n_clicks", "")
            try:
                triggered_id = json.loads(id_str)
            except json.JSONDecodeError:
                LOG.error("Failed to parse prop_id: %s", prop_id)
                raise PreventUpdate

    if not isinstance(triggered_id, dict):
        LOG.error("triggered_id is not a dict: %s", triggered_id)
        raise PreventUpdate

    invoice_id = triggered_id.get("index", "")
    if not invoice_id or not invoice_id.startswith("invoice-"):
        LOG.warning("Invalid invoice ID: %s", invoice_id)
        raise PreventUpdate

    # Extract invoice number from ID
    invoice_number = invoice_id.replace("invoice-", "")
    LOG.info("Download requested for invoice: %s", invoice_number)

    # Find the invoice in state
    page = _state_to_page(state)
    invoice = next(
        (inv for inv in page.items if inv.invoice.invoice_number == invoice_number),
        None,
    )

    if not invoice:
        LOG.warning("Invoice not found: %s", invoice_number)
        raise PreventUpdate

    if not invoice.path:
        LOG.warning("Invoice has no path: %s", invoice_number)
        raise PreventUpdate

    LOG.info("Downloading from path: %s", invoice.path)

    try:
        # Download file using workspace client
        workspace = clients.workspace_client()
        file_path = invoice.path

        # Convert DBFS path to workspace path format
        workspace_path = file_path
        if file_path.startswith("dbfs:/"):
            workspace_path = file_path[5:]  # Remove "dbfs:" prefix

        # Read file from workspace
        file_response = workspace.files.download(workspace_path)
        file_content = file_response.contents.read()

        # Extract filename from path
        filename = os.path.basename(file_path) if "/" in file_path else "invoice.pdf"

        LOG.info("Download successful: %s", filename)
        return dcc.send_bytes(file_content, filename=filename)

    except Exception as e:
        LOG.error("Error downloading file: %s", e, exc_info=True)
        raise PreventUpdate


# Initialize scroll listener and handle scroll events
# This callback watches the invoice-state and sets up scroll detection
app.clientside_callback(
    """
    function(state) {
        if (typeof window === "undefined") {
            return window.dash_clientside.no_update;
        }
        
        // Store current state for scroll handler to access
        window.__invoiceState = state;
        
        // Initialize scroll listener if not already done
        if (!window.__scrollListenerInitialized) {
            window.__invoiceScrollCount = 0;
            window.__invoiceScrollPending = false;
            
            function handleScroll() {
                const dash = window.dash_clientside;
                if (!dash || !dash.set_props) {
                    return;
                }
                
                // Check if we have more data using stored state
                const state = window.__invoiceState;
                if (!state || !state.has_more) {
                    window.__invoiceScrollPending = false;
                    return;
                }
                
                const doc = document.documentElement || document.body;
                const scrollTop = window.pageYOffset || doc.scrollTop || 0;
                const innerHeight = window.innerHeight || doc.clientHeight || 0;
                const scrollHeight = doc.scrollHeight || document.body.scrollHeight || 0;
                const threshold = 200;
                const nearBottom = scrollTop + innerHeight >= scrollHeight - threshold;
                
                if (nearBottom) {
                    if (!window.__invoiceScrollPending) {
                        window.__invoiceScrollPending = true;
                        window.__invoiceScrollCount += 1;
                        dash.set_props('scroll-trigger', {data: window.__invoiceScrollCount});
                    }
                } else {
                    window.__invoiceScrollPending = false;
                }
            }
            
            // Throttle scroll events
            let scrollTimeout;
            window.addEventListener('scroll', function() {
                if (scrollTimeout) {
                    clearTimeout(scrollTimeout);
                }
                scrollTimeout = setTimeout(handleScroll, 100);
            }, { passive: true });
            
            window.__scrollListenerInitialized = true;
        }
        
        // Reset pending flag when state changes (new data loaded)
        window.__invoiceScrollPending = false;
        
        return window.dash_clientside.no_update;
    }
    """,
    Output("scroll-trigger", "data", allow_duplicate=True),
    Input("invoice-state", "data"),
    prevent_initial_call="initial_duplicate",
)


def main() -> None:
    """Entrypoint used by uv via `uv run invoice_ui`."""
    if USE_LIVE:
        configs.get()
    app.run(debug=True, host="0.0.0.0", port=8000, dev_tools_hot_reload=False)


if __name__ == "__main__":
    main()
