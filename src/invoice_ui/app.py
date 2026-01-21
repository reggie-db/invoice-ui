"""
Dash application entry point for the Invoice Search UI.

This module initializes the Dash app, registers all callbacks for search,
pagination, file downloads, and real-time Genie AI status updates via WebSocket.

The application supports two operational modes:
- Demo mode: Uses static invoice data (INVOICE_UI_USE_LIVE=false)
- Production mode: Connects to Databricks Spark and optional Genie AI

Key Callbacks:
- update_invoice_state: Handles search and infinite scroll pagination
- render_results: Renders invoice cards or Genie table based on state
- handle_download: Downloads invoice PDFs from DBFS/Volumes
- update_genie_display: Updates UI based on WebSocket Genie status messages

Client-side callbacks handle:
- URL fragment sync for shareable search queries
- Loading states during search
- Scroll detection for infinite loading
- AG Grid CSV export
"""

import io
import json
import os
from pathlib import Path

from dash import ALL, Dash, Input, Output, State, callback_context, dcc
from dash.exceptions import PreventUpdate

from invoice_ui.components.invoice_results import build_invoice_results
from invoice_ui.layout import build_layout
from invoice_ui.lib import clients, logs
from invoice_ui.models.common import AppState, GenieStatusMessage
from invoice_ui.models.invoice import (
    deserialize_page,
    serialize_invoice,
    serialize_page,
)
from invoice_ui.services import get_invoice_service
from invoice_ui.ws_server import init_websocket

LOG = logs.logger(__file__)

# Configuration from environment
PAGE_SIZE = 10
APP_PORT = int(os.getenv("DATABRICKS_APP_PORT", "8000"))
USE_LIVE = os.getenv("INVOICE_UI_USE_LIVE", "true").lower() in {"1", "true", "yes"}
USE_GENERIC_BRANDING = os.getenv("INVOICE_UI_GENERIC", "false").lower() in {
    "1",
    "true",
    "yes",
}

# Branding configuration
APP_TITLE = "Invoice Search" if USE_GENERIC_BRANDING else "Hardware Invoice Search"

# Configure invoice table name
_INVOICE_TABLE_NAME_KEY = "INVOICE_TABLE_NAME"
_DEFAULT_INVOICE_TABLE_NAME = "reggie_pierce.invoice_pipeline_dev.info_parse"
if not os.environ.get(_INVOICE_TABLE_NAME_KEY, None):
    os.environ[_INVOICE_TABLE_NAME_KEY] = _DEFAULT_INVOICE_TABLE_NAME
_INVOICE_TABLE_NAME = os.environ[_INVOICE_TABLE_NAME_KEY]
LOG.info("%s: %s", _INVOICE_TABLE_NAME_KEY, _INVOICE_TABLE_NAME)

# Configure genie space id
_INVOICE_GENIE_SPACE_ID_KEY = "INVOICE_GENIE_SPACE_ID"
if _INVOICE_TABLE_NAME == _DEFAULT_INVOICE_TABLE_NAME:
    if not os.environ.get(_INVOICE_GENIE_SPACE_ID_KEY, None):
        os.environ[_INVOICE_GENIE_SPACE_ID_KEY] = "01f0cfa53c571bbb9b36f0e14a4e408d"
LOG.info(
    "%s: %s",
    _INVOICE_GENIE_SPACE_ID_KEY,
    os.environ.get(_INVOICE_GENIE_SPACE_ID_KEY, None),
)

_service = get_invoice_service("impl" if USE_LIVE else "demo")
_assets_path = Path(__file__).resolve().parents[2] / "assets"

app = Dash(
    __name__,
    title=APP_TITLE,
    assets_folder=str(_assets_path),
    update_title=None,
)

# Theme configuration for index string
_THEME_CLASS = "theme-generic" if USE_GENERIC_BRANDING else ""
_FAVICON = "favicon-generic.ico" if USE_GENERIC_BRANDING else "favicon.ico"
_FONT_URL = (
    "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap"
    if USE_GENERIC_BRANDING
    else "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Source+Sans+3:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap"
)

# Set custom index string with fonts and syntax highlighting
app.index_string = f"""<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}
        <title>{{%title%}}</title>
        <link rel="icon" type="image/x-icon" href="/assets/{_FAVICON}">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="{_FONT_URL}" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
        {{%css%}}
    </head>
    <body class="{_THEME_CLASS}">
        {{%app_entry%}}
        <footer>
            {{%config%}}
            {{%scripts%}}
            {{%renderer%}}
            <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/sql.min.js"></script>
            <script>
                // Auto-highlight SQL code blocks when DOM changes
                const observer = new MutationObserver(() => {{
                    document.querySelectorAll('code.language-sql:not(.hljs)').forEach((el) => {{
                        hljs.highlightElement(el);
                    }});
                }});
                observer.observe(document.body, {{ childList: true, subtree: true }});
                // Initial highlight
                document.addEventListener('DOMContentLoaded', () => {{
                    document.querySelectorAll('code.language-sql').forEach((el) => {{
                        hljs.highlightElement(el);
                    }});
                }});
            </script>
        </footer>
    </body>
</html>"""


# Initialize WebSocket on Flask server (same port as Dash app)
init_websocket(app.server)
LOG.info("WebSocket initialized on /ws/genie")


# Check if AI search is available
AI_AVAILABLE = _service.ai_available

app.layout = build_layout(ai_available=AI_AVAILABLE)


# Build callback inputs based on whether AI is available
_search_inputs = [
    Input("search-query", "value"),
    Input("scroll-trigger", "data"),
    Input("initial-load-trigger", "data"),
]
_search_states = [State("invoice-state", "data")]

if AI_AVAILABLE:
    _search_states.append(State("ai-search-toggle", "value"))


@app.callback(
    Output("invoice-state", "data"),
    _search_inputs,
    _search_states,
    prevent_initial_call=False,
)
def update_invoice_state(
    query: str | None,
    scroll_counter: int | None,
    initial_trigger: int | None,
    state_dict: dict | None,
    ai_toggle: list | None = None,
) -> dict:
    """
    Handle initial load, filter changes, and scroll-based lazy loading.

    This is the primary callback that manages application state. It responds to:
    - Initial page load (initial_trigger)
    - Search query changes (search-query input)
    - Scroll events for infinite pagination (scroll-trigger)

    Args:
        query: Current search query string from the input field.
        scroll_counter: Counter incremented by client-side scroll detection.
        initial_trigger: Set to 1 on initial load to trigger first data fetch.
        state_dict: Current serialized AppState from dcc.Store.
        ai_toggle: List containing 'enabled' if AI search is active.

    Returns:
        Serialized state dictionary for dcc.Store containing items, pagination,
        and optional Genie table results.

    Raises:
        PreventUpdate: When callback should not update state (no trigger, etc.)
    """
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    # Determine if AI search is enabled (default True if available)
    use_ai = AI_AVAILABLE and (ai_toggle is None or "enabled" in (ai_toggle or []))

    # Initial load or search query change: fetch first page
    if trigger == "initial-load-trigger" or trigger == "search-query":
        query_text = (query or "").strip()
        # Clear any previous genie table before searching
        _service.clear_genie_table()
        page = _service.list_invoices(
            query=query_text or None,
            page=1,
            page_size=PAGE_SIZE,
            use_ai=use_ai,
        )
        # Get any genie table result that was captured during the search
        genie_table = _service.get_last_genie_table()
        return serialize_page(page, query_text, scroll_counter or 0, genie_table)

    # Scroll-triggered pagination
    if trigger == "scroll-trigger":
        state = AppState.from_dict(state_dict)
        if not state.has_more:
            raise PreventUpdate
        if scroll_counter is None or scroll_counter == state.scroll_token:
            raise PreventUpdate

        next_page_num = state.page + 1
        query_text = state.query
        new_page = _service.list_invoices(
            query=query_text or None,
            page=next_page_num,
            page_size=state.page_size,
            use_ai=use_ai,
        )
        # Combine items from previous state with new page items
        combined_items = state.items + [
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
def render_results(state_dict: dict) -> object:
    """
    Render invoice results whenever the backing store changes.

    Converts the serialized state back to model objects and builds the
    appropriate UI: invoice cards, Genie table, or empty state.

    Args:
        state_dict: Serialized AppState from dcc.Store.

    Returns:
        Dash component tree for the results container.

    Raises:
        PreventUpdate: When state is empty (initial load not complete).
    """
    if not state_dict:
        raise PreventUpdate
    state = AppState.from_dict(state_dict)
    return build_invoice_results(
        deserialize_page(state_dict),
        state.query,
        state.has_more,
        genie_table=state.genie_table,
    )


# Client-side callback: Show loading spinner immediately when search starts.
# This runs in the browser before the server callback completes, providing
# instant visual feedback to the user.
app.clientside_callback(
    """
    function(query, currentChildren) {
        if (query === undefined || query === null) {
            return window.dash_clientside.no_update;
        }
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
                                props: { className: 'loading-spinner-large' }
                            },
                            {
                                type: 'Span',
                                namespace: 'dash_html_components',
                                props: { children: 'Searching...', className: 'loading-text' }
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


# Set WebSocket URL dynamically based on current page location
app.clientside_callback(
    """
    function(wsConfig, pathname) {
        if (!wsConfig || !wsConfig.path) return '';
        const loc = window.location;
        const protocol = loc.protocol === 'https:' ? 'wss:' : 'ws:';
        return protocol + '//' + loc.host + wsConfig.path;
    }
    """,
    Output("genie-ws", "url"),
    Input("ws-url-store", "data"),
    Input("url", "pathname"),
)


@app.callback(
    Output("genie-status", "className"),
    Output("genie-status-text", "children"),
    Output("genie-status-message", "children"),
    Input("genie-ws", "message"),
    prevent_initial_call=True,
)
def update_genie_display(msg: dict | None) -> tuple[str, str, str]:
    """
    Update the Genie status UI based on WebSocket messages.

    Parses incoming WebSocket messages and updates the status indicator
    that appears below the search input during AI-powered searches.

    Args:
        msg: WebSocket message dict with 'data' key containing JSON payload.

    Returns:
        Tuple of (className, status_text, message_text) for the status UI.
        Returns hidden state if message is invalid or inactive.
    """
    if not msg:
        return "genie-status hidden", "", ""

    try:
        data = json.loads(msg.get("data", "{}"))
        status = GenieStatusMessage.from_dict(data)
    except (json.JSONDecodeError, TypeError):
        return "genie-status hidden", "", ""

    if not status.active:
        return "genie-status hidden", "", ""

    return (
        "genie-status",
        status.status or "Processing...",
        status.message or "",
    )


# Hash decode logic for URL fragment handling
# Decodes { q: "query", ai: true/false } from base64-encoded JSON
_DECODE_HASH_QUERY_FN = """
    function(trigger) {
        if (typeof window === "undefined" || !window.__decodeHashState) return '';
        return window.__decodeHashState().q || '';
    }
"""

# Initialize hash router and read initial hash on page load
app.clientside_callback(
    _DECODE_HASH_QUERY_FN,
    Output("search-query", "value"),
    Input("url", "pathname"),
    prevent_initial_call=False,
)

# Listen for hash changes and sync search query with Dash
app.clientside_callback(
    _DECODE_HASH_QUERY_FN,
    Output("search-query", "value", allow_duplicate=True),
    Input("url", "hash"),
    prevent_initial_call=True,
)

# Register AI toggle hash callbacks only if AI is available
if AI_AVAILABLE:
    # Decode AI state from hash on page load
    app.clientside_callback(
        """
        function(trigger) {
            if (typeof window === "undefined" || !window.__decodeHashState) return ['enabled'];
            const state = window.__decodeHashState();
            return state.ai !== false ? ['enabled'] : [];
        }
        """,
        Output("ai-search-toggle", "value"),
        Input("url", "pathname"),
        prevent_initial_call=False,
    )

    # Listen for hash changes and sync AI toggle with Dash
    app.clientside_callback(
        """
        function(trigger) {
            if (typeof window === "undefined" || !window.__decodeHashState) {
                return window.dash_clientside.no_update;
            }
            const state = window.__decodeHashState();
            return state.ai !== false ? ['enabled'] : [];
        }
        """,
        Output("ai-search-toggle", "value", allow_duplicate=True),
        Input("url", "hash"),
        prevent_initial_call=True,
    )

    # Update hash when search query or AI toggle changes
    app.clientside_callback(
        """
        function(query, aiToggle) {
            if (typeof window === "undefined") {
                return window.dash_clientside.no_update;
            }
            if (window.__updateHashFromState) {
                const aiEnabled = aiToggle && aiToggle.includes('enabled');
                window.__updateHashFromState(query || '', aiEnabled);
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("url", "hash", allow_duplicate=True),
        Input("search-query", "value"),
        Input("ai-search-toggle", "value"),
        prevent_initial_call=True,
    )
else:
    # Update hash when search query changes (no AI toggle)
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


# Handle download button clicks - show spinner and trigger download
app.clientside_callback(
    """
    function(n_clicks, state) {
        if (!n_clicks || n_clicks.every(n => !n) || !state) {
            return [window.dash_clientside.no_update, window.dash_clientside.no_update];
        }
        
        const triggeredId = dash_clientside.callback_context.triggered_id;
        if (!triggeredId || !triggeredId.index) {
            return [window.dash_clientside.no_update, window.dash_clientside.no_update];
        }
        
        const invoiceId = triggeredId.index;
        if (!invoiceId.startsWith('invoice-')) {
            return [window.dash_clientside.no_update, window.dash_clientside.no_update];
        }
        
        const invoiceNumber = invoiceId.replace('invoice-', '');
        const items = state.items || [];
        const invoice = items.find(inv => 
            inv.invoice && inv.invoice.invoice_number === invoiceNumber
        );
        
        if (!invoice || !invoice.path) {
            console.error('Invoice or path not found');
            return [window.dash_clientside.no_update, window.dash_clientside.no_update];
        }
        
        // Show spinner on the clicked button
        const button = document.querySelector(`button[id*='"index":"${invoiceId}"']`);
        if (button) {
            button.disabled = true;
            button.classList.add('downloading');
        }
        
        // Store path for server callback and trigger download
        return [invoice.path, Date.now()];
    }
    """,
    [Output("download-path-store", "data"), Output("download-trigger", "data")],
    Input({"type": "download-button", "index": ALL}, "n_clicks"),
    State("invoice-state", "data"),
    prevent_initial_call=True,
)


@app.callback(
    Output("download-file", "data"),
    Input("download-trigger", "data"),
    State("download-path-store", "data"),
    prevent_initial_call=True,
)
def handle_download(trigger: int | None, file_path: str | None) -> dict | None:
    """
    Handle invoice PDF file download via dcc.Download component.

    Attempts to download the file using Spark first (for DBFS/Volumes access),
    falling back to Databricks Workspace client if Spark is unavailable.

    Args:
        trigger: Timestamp indicating download was requested.
        file_path: DBFS or Volumes path to the PDF file.

    Returns:
        Dictionary for dcc.send_bytes with file content and filename.

    Raises:
        PreventUpdate: When trigger or file_path is empty, or on download error.
    """
    if not trigger or not file_path:
        raise PreventUpdate

    LOG.info("Download triggered for: %s", file_path)

    try:
        dbfs_prefix = "dbfs:"
        clean_path = file_path
        if clean_path.startswith(dbfs_prefix):
            clean_path = clean_path[len(dbfs_prefix) :]

        filename = os.path.basename(file_path) if "/" in file_path else "invoice.pdf"

        # Try Spark first in Databricks App environment
        try:
            LOG.info("Using Spark for download")

            def _generate(writer: io.BytesIO) -> None:
                spark = clients.spark()
                df = spark.read.format("binaryFile").load(file_path)
                row = df.collect()[0]
                writer.write(row.content)

            return dcc.send_bytes(_generate, filename)
        except Exception:
            LOG.warning("Spark download failed", exc_info=True)

        # Fall back to workspace client
        LOG.info("Using workspace client for download")
        workspace = clients.workspace_client()
        file_response = workspace.files.download(clean_path)
        content = file_response.contents.read()
        return dcc.send_bytes(content, filename)

    except Exception as e:
        LOG.error("Download error: %s", e, exc_info=True)
        raise PreventUpdate from e


# Hide spinner after download completes
app.clientside_callback(
    """
    function(data) {
        // Re-enable all download buttons and remove spinner
        document.querySelectorAll('.download-button.downloading').forEach(btn => {
            btn.disabled = false;
            btn.classList.remove('downloading');
        });
        return window.dash_clientside.no_update;
    }
    """,
    Output("download-trigger", "data", allow_duplicate=True),
    Input("download-file", "data"),
    prevent_initial_call=True,
)


# Export AG Grid to CSV when export button is clicked
app.clientside_callback(
    """
    function(n_clicks) {
        if (!n_clicks || n_clicks <= 0) {
            return window.dash_clientside.no_update;
        }
        try {
            const gridApi = dash_ag_grid.getApi('genie-results-grid');
            if (gridApi) {
                gridApi.exportDataAsCsv({
                    fileName: 'genie_results.csv'
                });
            }
        } catch (e) {
            console.warn('AG Grid export failed:', e);
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("genie-export-csv-btn", "n_clicks", allow_duplicate=True),
    Input("genie-export-csv-btn", "n_clicks"),
    prevent_initial_call=True,
)


# Initialize scroll listener and handle scroll events
app.clientside_callback(
    """
    function(state) {
        if (typeof window === "undefined") return window.dash_clientside.no_update;
        
        window.__invoiceState = state;
        
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
        
        window.__invoiceScrollPending = false;
        const hint = document.getElementById('load-more-hint');
        const spinner = document.getElementById('load-more-spinner');
        if (hint) hint.classList.remove('loading');
        if (spinner) spinner.classList.add('hidden');
        
        requestAnimationFrame(() => setTimeout(triggerLoad, 200));
        
        return window.dash_clientside.no_update;
    }
    """,
    Output("scroll-trigger", "data", allow_duplicate=True),
    Input("invoice-state", "data"),
    prevent_initial_call="initial_duplicate",
)


def main() -> None:
    """
    Application entrypoint used by uv via `uv run invoice_ui`.

    Starts the Dash development server with hot reload disabled for stability.
    Production deployments should use a WSGI server like gunicorn.
    """
    app.run(debug=True, host="0.0.0.0", port=APP_PORT, dev_tools_hot_reload=False)


if __name__ == "__main__":
    main()
