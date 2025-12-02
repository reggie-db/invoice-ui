from __future__ import annotations

import os
from pathlib import Path

from dash import Dash, Input, Output, State, callback_context, dcc
from dash.exceptions import PreventUpdate
from reggie_core import logs
from reggie_tools import clients, configs

from invoice_ui.components.invoice_results import build_invoice_results
from invoice_ui.layout import build_layout
from invoice_ui.models.invoice import (
    Invoice,
    InvoicePage,
    deserialize_invoice,
    serialize_invoice,
)
from invoice_ui.services import get_invoice_service

"""Dash application entry point for the invoice search UI."""

LOG = logs.logger(__file__)

PAGE_SIZE = 5
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


def _page_to_state(page: InvoicePage, query: str, scroll_token: int) -> dict:
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


def _state_to_invoices(state: dict) -> list[Invoice]:
    """Convert stored invoice dictionaries back into Invoice dataclasses."""
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
    Input({"type": "download-button", "index": "ALL"}, "n_clicks"),
    State("invoice-state", "data"),
    prevent_initial_call=True,
)
def handle_download(n_clicks_list: list[int | None], state: dict | None) -> dict | None:
    """Handle PDF download when download button is clicked."""
    LOG.info(
        "handle_download called - n_clicks_list: %s, state: %s",
        n_clicks_list,
        bool(state),
    )

    ctx = callback_context
    LOG.info("triggered: %s", ctx.triggered if ctx.triggered else "None")
    LOG.info(
        "triggered_id: %s", ctx.triggered_id if hasattr(ctx, "triggered_id") else "N/A"
    )

    if not state or not n_clicks_list:
        LOG.warning("Missing state or n_clicks_list")
        raise PreventUpdate

    if not ctx.triggered:
        LOG.warning("No triggers")
        raise PreventUpdate

    # Find which button was clicked using triggered_id (pattern matching)
    try:
        # For pattern matching, triggered_id might be None, so check prop_id instead
        prop_id = ctx.triggered[0]["prop_id"]
        LOG.info("prop_id: %s", prop_id)

        triggered_id = ctx.triggered_id
        LOG.info("triggered_id: %s", triggered_id)

        # Parse the prop_id to extract the ID dictionary
        # Format: '{"type":"download-button","index":"invoice-123"}.n_clicks'
        if prop_id and ".n_clicks" in prop_id:
            import json

            id_str = prop_id.replace(".n_clicks", "")
            try:
                trigger_dict = json.loads(id_str)
                invoice_id = trigger_dict.get("index", "")
                LOG.info("Parsed invoice_id from prop_id: %s", invoice_id)
            except json.JSONDecodeError:
                LOG.error("Failed to parse prop_id as JSON: %s", id_str)
                raise PreventUpdate
        elif triggered_id and isinstance(triggered_id, dict):
            invoice_id = triggered_id.get("index", "")
            LOG.info("Got invoice_id from triggered_id: %s", invoice_id)
        else:
            LOG.warning(
                "Could not extract invoice_id - prop_id: %s, triggered_id: %s",
                prop_id,
                triggered_id,
            )
            raise PreventUpdate

        if not invoice_id or not invoice_id.startswith("invoice-"):
            LOG.warning("Invalid invoice ID: %s", invoice_id)
            raise PreventUpdate

        # Extract invoice number from ID
        invoice_number = invoice_id.replace("invoice-", "")
        LOG.info("Looking for invoice number: %s", invoice_number)

        # Find the invoice in state
        invoices = _state_to_invoices(state)
        LOG.info("Total invoices in state: %d", len(invoices))
        invoice = next(
            (inv for inv in invoices if inv.invoice.invoice_number == invoice_number),
            None,
        )

        if not invoice:
            LOG.warning("Invoice not found for number: %s", invoice_number)
            raise PreventUpdate

        if not invoice.path:
            LOG.warning("Invoice found but path is empty: %s", invoice_number)
            raise PreventUpdate

        LOG.info("Found invoice with path: %s", invoice.path)

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
        file_content = file_response.as_bytes()

        # Extract filename from path
        filename = os.path.basename(file_path) if "/" in file_path else "invoice.pdf"

        # Return file data for download
        return dcc.send_bytes(file_content, file_name=filename)

    except Exception as e:
        LOG.error("Error downloading file: %s", e, exc_info=True)
        raise PreventUpdate


# Initialize scroll listener on page load
app.clientside_callback(
    """
    function(n) {
        if (typeof window === "undefined") {
            return 0;
        }
        
        // Initialize scroll listener if not already done
        if (!window.__scrollListenerInitialized) {
            window.__invoiceScrollCount = 0;
            window.__invoiceScrollPending = false;
            
            function handleScroll() {
                const dash = window.dash_clientside;
                if (!dash || !dash.set_props) {
                    return;
                }
                
                // Get current state to check if we have more data
                const state = dash.get_props('invoice-state', 'data');
                if (!state || !state.has_more) {
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
        
        return window.__invoiceScrollCount || 0;
    }
    """,
    Output("scroll-trigger", "data"),
    Input("url", "pathname"),
    prevent_initial_call=False,
)


def main() -> None:
    """Entrypoint used by uv via `uv run invoice_ui`."""
    if USE_LIVE:
        configs.get()
    app.run(debug=True, host="0.0.0.0", port=8000, dev_tools_hot_reload=False)


if __name__ == "__main__":
    main()
