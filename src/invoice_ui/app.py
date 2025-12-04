import os
from pathlib import Path

from dash import ALL, MATCH, Dash, Input, Output, State, callback_context, dcc
from dash.exceptions import PreventUpdate
from reggie_core import logs, objects
from reggie_tools import clients, configs

from invoice_ui.components.invoice_results import build_invoice_results
from invoice_ui.layout import build_grid_tab, build_layout, build_search_tab
from invoice_ui.models.invoice import (
    GenieStatus,
    deserialize_page,
    serialize_invoice,
    serialize_page,
)
from invoice_ui.services import get_invoice_service

"""Dash application entry point for the invoice search UI."""

LOG = logs.logger(__file__)

PAGE_SIZE = 10
USE_LIVE = os.getenv("INVOICE_UI_USE_LIVE", "true").lower() in {"1", "true", "yes"}

_service = get_invoice_service("impl" if USE_LIVE else "demo")
_assets_path = Path(__file__).resolve().parents[2] / "assets"

app = Dash(
    __name__,
    title="Hardware Invoice Search",
    assets_folder=str(_assets_path),
    update_title=None,
    suppress_callback_exceptions=True,  # Allow dynamic tab content
)

# Set custom index string with fonts and Vaadin React Grid bundle
app.index_string = """<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        <link rel="icon" type="image/x-icon" href="/assets/favicon.ico">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
            <!-- Vaadin React Grid bundle (loaded after Dash React) -->
            <script src="/assets/vaadin_grid.min.js"></script>
        </footer>
    </body>
</html>"""


# Initialize with query from URL fragment if present
_initial_query = ""
_initial_page = _service.list_invoices(
    query=_initial_query or None, page=1, page_size=PAGE_SIZE
)
app.layout = build_layout(_initial_page, _initial_query)


# Tab switching callback
@app.callback(
    Output("tab-content", "children"),
    Input("app-tabs", "value"),
)
def render_tab_content(tab: str):
    """Render content based on selected tab."""
    if tab == "grid-tab":
        return build_grid_tab()
    # Default to search tab
    return build_search_tab(_initial_page, _initial_query)


# Generate dummy data for grid (server-side)
def _generate_grid_data(count: int = 1000, start_id: int = 1) -> list[dict]:
    """Generate dummy data for the grid demo."""
    departments = ["Engineering", "Marketing", "Sales", "HR", "Finance", "Operations"]
    statuses = ["Active", "On Leave", "Remote", "Contract"]
    first_names = ["Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Henry"]
    last_names = [
        "Johnson",
        "Smith",
        "White",
        "Brown",
        "Davis",
        "Wilson",
        "Taylor",
        "Lee",
    ]

    data = []
    for i in range(start_id, start_id + count):
        first = first_names[i % len(first_names)]
        last = last_names[(i * 7) % len(last_names)]
        data.append(
            {
                "id": i,
                "name": f"{first} {last}",
                "email": f"{first.lower()}.{last.lower()}{i}@example.com",
                "department": departments[i % len(departments)],
                "status": statuses[i % len(statuses)],
            }
        )
    return data


@app.callback(
    Output("vaadin-grid", "pageItems"),
    Output("vaadin-grid", "totalCount"),
    Input("vaadin-grid", "requestedPage"),
    State("vaadin-grid", "requestedPageSize"),
    prevent_initial_call=False,
)
def load_grid_page(
    page: int | None,
    page_size: int | None,
) -> tuple[dict, int]:
    """Load grid data page on demand (lazy loading via dataProvider)."""
    import time

    if page is None:
        page = 0

    size = page_size or 50
    start = page * size
    total = 1000

    time.sleep(0.5)  # Simulate server delay
    LOG.info(f"Loading grid page {page} (items {start + 1} to {start + size})")

    # Generate items for this page
    items = _generate_grid_data(size, start_id=start + 1)

    return {"page": page, "items": items}, total


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
    return build_invoice_results(
        deserialize_page(state), state.get("query", ""), state.get("has_more", False)
    )


# Clear results immediately when search starts (before server responds)
app.clientside_callback(
    """
    function(query, currentChildren) {
        // Only clear on actual search changes, not initial load
        if (query === undefined || query === null) {
            return window.dash_clientside.no_update;
        }
        // Return a loading placeholder
        return {
            props: {
                className: 'results-loading',
                children: {
                    props: {
                        className: 'loading-placeholder',
                        children: [
                            {
                                type: 'Div',
                                namespace: 'dash_html_components',
                                props: {
                                    className: 'loading-spinner-large'
                                }
                            },
                            {
                                type: 'Span',
                                namespace: 'dash_html_components',
                                props: {
                                    children: 'Searching...',
                                    className: 'loading-text'
                                }
                            }
                        ]
                    },
                    type: 'Div',
                    namespace: 'dash_html_components'
                }
            },
            type: 'Div',
            namespace: 'dash_html_components'
        };
    }
    """,
    Output("results-container", "children", allow_duplicate=True),
    Input("search-query", "value"),
    State("results-container", "children"),
    prevent_initial_call=True,
)


# Check if genie is configured
_GENIE_ENABLED = bool(os.getenv("INVOICE_GENIE_SPACE_ID", ""))


# Enable genie status polling when search starts
@app.callback(
    Output("genie-status-interval", "disabled"),
    Input("search-query", "value"),
    Input("genie-status-store", "data"),
    State("genie-status-interval", "disabled"),
    prevent_initial_call=True,
)
def toggle_genie_polling(
    query: str | None, status: dict, currently_disabled: bool
) -> bool:
    """Enable polling when search starts, disable when genie is not active."""
    if not _GENIE_ENABLED:
        return True
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    # Enable polling when search changes (with actual query text)
    if trigger == "search-query" and query and query.strip():
        return False
    # Only disable when genie becomes inactive
    if trigger == "genie-status-store":
        if not status.get("active", False):
            return True
        # Keep polling while active
        return False
    raise PreventUpdate


# Poll for genie status
@app.callback(
    Output("genie-status-store", "data"),
    Input("genie-status-interval", "n_intervals"),
    prevent_initial_call=True,
)
def poll_genie_status(n_intervals: int) -> dict:
    """Poll the service for current genie status."""
    if not _GENIE_ENABLED:
        genie_status = GenieStatus(None)
    else:
        from invoice_ui.services.invoice_service_impl import InvoiceServiceImpl

        genie_status = InvoiceServiceImpl.get_genie_status()
    return objects.dump(genie_status)


# Update genie status display
@app.callback(
    Output("genie-status", "className"),
    Output("genie-status-text", "children"),
    Output("genie-status-message", "children"),
    Input("genie-status-store", "data"),
    prevent_initial_call=True,
)
def update_genie_display(status: dict) -> tuple[str, str, str]:
    """Update the genie status UI based on current status."""
    if not status.get("active", False):
        return "genie-status hidden", "", ""
    return (
        "genie-status",
        status.get("status", "Processing..."),
        status.get("message", ""),
    )


# Shared hash decode logic - must be a complete function for each callback
_DECODE_HASH_FN = """
    function(trigger) {
        const hash = window.location.hash.substring(1);
        if (!hash || !hash.startsWith('search/')) return '';
        try {
            const encoded = hash.substring(7);
            const padding = 4 - (encoded.length % 4);
            return atob(padding !== 4 ? encoded + '='.repeat(padding) : encoded);
        } catch (e) {
            return '';
        }
    }
"""

# Initialize hash router and read initial hash on page load
app.clientside_callback(
    _DECODE_HASH_FN,
    Output("search-query", "value"),
    Input("url", "pathname"),
    prevent_initial_call=False,
)

# Listen for hash changes and sync with Dash
app.clientside_callback(
    _DECODE_HASH_FN,
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


# Show spinner and disable button when download is clicked
app.clientside_callback(
    """
    function(n_clicks) {
        if (!n_clicks || n_clicks === 0) {
            return [window.dash_clientside.no_update, window.dash_clientside.no_update];
        }
        // Show spinner and disable button
        return ["download-spinner", true];
    }
    """,
    [
        Output({"type": "download-spinner", "index": MATCH}, "className"),
        Output({"type": "download-button", "index": MATCH}, "disabled"),
    ],
    Input({"type": "download-button", "index": MATCH}, "n_clicks"),
    prevent_initial_call=True,
)

# Hide spinner and re-enable buttons when download completes
app.clientside_callback(
    """
    function(data) {
        // Hide all spinners and re-enable all buttons when download completes
        const spinners = document.querySelectorAll('.download-spinner');
        spinners.forEach(s => s.classList.add('hidden'));
        const buttons = document.querySelectorAll('.download-button');
        buttons.forEach(b => b.disabled = false);
        return window.dash_clientside.no_update;
    }
    """,
    Output("download-file", "data", allow_duplicate=True),
    Input("download-file", "data"),
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
    ctx = callback_context

    # Check if any button was actually clicked (not just initial render)
    if not n_clicks_list or all(n is None or n == 0 for n in n_clicks_list):
        raise PreventUpdate

    if not ctx.triggered or not state:
        raise PreventUpdate

    # Get the triggered button's ID from context
    triggered_id = ctx.triggered_id

    # triggered_id is a dict like {"type": "download-button", "index": "invoice-123"}
    invoice_id = triggered_id.get("index", "")
    if not invoice_id.startswith("invoice-"):
        raise PreventUpdate

    # Extract invoice number from ID
    invoice_number = invoice_id.replace("invoice-", "")
    LOG.info("Download requested for invoice: %s", invoice_number)

    # Find the invoice in state
    page = deserialize_page(state)
    invoice = next(
        (inv for inv in page.items if inv.invoice.invoice_number == invoice_number),
        None,
    )

    if not invoice or not invoice.path:
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
app.clientside_callback(
    """
    function(state) {
        if (typeof window === "undefined") return window.dash_clientside.no_update;
        
        window.__invoiceState = state;
        
        // Shared: check if should load more and trigger if needed
        function shouldLoadMore() {
            const st = window.__invoiceState;
            if (!st || !st.has_more || window.__invoiceScrollPending) return false;
            const doc = document.documentElement || document.body;
            const scrollTop = window.pageYOffset || doc.scrollTop || 0;
            const viewHeight = window.innerHeight || doc.clientHeight || 0;
            const scrollHeight = doc.scrollHeight || document.body.scrollHeight || 0;
            return scrollTop + viewHeight >= scrollHeight - 400 || scrollHeight <= viewHeight + 100;
        }
        
        function triggerLoad() {
            const dash = window.dash_clientside;
            if (!dash || !dash.set_props || !shouldLoadMore()) return;
            window.__invoiceScrollPending = true;
            window.__invoiceScrollCount += 1;
            const hint = document.getElementById('load-more-hint');
            const spinner = document.getElementById('load-more-spinner');
            if (hint) hint.classList.add('loading');
            if (spinner) spinner.classList.remove('hidden');
            dash.set_props('scroll-trigger', {data: window.__invoiceScrollCount});
        }
        
        // Initialize scroll listener once
        if (!window.__scrollListenerInitialized) {
            window.__invoiceScrollCount = 0;
            window.__invoiceScrollPending = false;
            
            let scrollTimeout;
            window.addEventListener('scroll', function() {
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(triggerLoad, 50);
            }, { passive: true });
            
            window.addEventListener('load', () => setTimeout(triggerLoad, 300));
            window.__scrollListenerInitialized = true;
        }
        
        // Reset and hide loading on state change
        window.__invoiceScrollPending = false;
        const hint = document.getElementById('load-more-hint');
        const spinner = document.getElementById('load-more-spinner');
        if (hint) hint.classList.remove('loading');
        if (spinner) spinner.classList.add('hidden');
        
        // Check if we need to load more immediately after DOM update
        requestAnimationFrame(() => setTimeout(triggerLoad, 200));
        
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
