import json
import os
from pathlib import Path

from dash import ALL, MATCH, Dash, Input, Output, State, callback_context, dcc
from dash.exceptions import PreventUpdate
from reggie_core import logs
from reggie_tools import clients, configs

from invoice_ui.components.invoice_results import build_invoice_results
from invoice_ui.layout import build_layout
from invoice_ui.models.common import AppState, GenieStatusMessage
from invoice_ui.models.invoice import (
    deserialize_page,
    serialize_invoice,
    serialize_page,
)
from invoice_ui.services import get_invoice_service
from invoice_ui.ws_server import init_websocket

"""
Dash application entry point for the invoice search UI.

This module initializes the Dash app, defines callbacks for search, pagination,
file downloads, and real-time status updates via WebSocket.
"""

LOG = logs.logger(__file__)

# Configuration from environment
PAGE_SIZE = 10
APP_PORT = int(os.getenv("INVOICE_UI_PORT", "8000"))
USE_LIVE = os.getenv("INVOICE_UI_USE_LIVE", "true").lower() in {"1", "true", "yes"}
USE_GENERIC_BRANDING = os.getenv("INVOICE_UI_GENERIC", "false").lower() in {
    "1",
    "true",
    "yes",
}

# Branding configuration
APP_TITLE = "Invoice Search" if USE_GENERIC_BRANDING else "Hardware Invoice Search"

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
_FONT_URL = (
    "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap"
    if USE_GENERIC_BRANDING
    else "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Source+Sans+3:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap"
)

# Set custom index string with fonts
app.index_string = f"""<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}
        <title>{{%title%}}</title>
        <link rel="icon" type="image/x-icon" href="/assets/favicon.ico">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="{_FONT_URL}" rel="stylesheet">
        {{%css%}}
    </head>
    <body class="{_THEME_CLASS}">
        {{%app_entry%}}
        <footer>
            {{%config%}}
            {{%scripts%}}
            {{%renderer%}}
        </footer>
    </body>
</html>"""


# Initialize WebSocket on Flask server (same port as Dash app)
init_websocket(app.server)
LOG.info("WebSocket initialized on /ws/genie")

# Initialize with query from URL fragment if present
_initial_query = ""
_initial_page = _service.list_invoices(
    query=_initial_query or None, page=1, page_size=PAGE_SIZE
)

app.layout = build_layout(_initial_page, _initial_query)


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
    state_dict: dict | None,
) -> dict:
    """Handle both filter changes and scroll-based lazy loading."""
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate

    state = AppState.from_dict(state_dict)
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger == "search-query":
        query_text = (query or "").strip()
        page = _service.list_invoices(
            query=query_text or None,
            page=1,
            page_size=state.page_size,
        )
        return serialize_page(page, query_text, scroll_counter or 0)

    if trigger == "scroll-trigger":
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
    """Render invoice results whenever the backing store changes."""
    if not state_dict:
        raise PreventUpdate
    state = AppState.from_dict(state_dict)
    return build_invoice_results(
        deserialize_page(state_dict), state.query, state.has_more
    )


# Clear results immediately when search starts (before server responds)
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
    """Update the status UI based on WebSocket messages."""
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


# Shared hash decode logic for URL fragment handling
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
def handle_download(
    n_clicks_list: list[int | None], state_dict: dict | None
) -> dict | None:
    """Handle PDF download when download button is clicked."""
    ctx = callback_context

    if not n_clicks_list or all(n is None or n == 0 for n in n_clicks_list):
        raise PreventUpdate

    if not ctx.triggered or not state_dict:
        raise PreventUpdate

    triggered_id = ctx.triggered_id
    invoice_id = triggered_id.get("index", "")
    if not invoice_id.startswith("invoice-"):
        raise PreventUpdate

    invoice_number = invoice_id.replace("invoice-", "")
    LOG.info("Download requested for invoice: %s", invoice_number)

    page = deserialize_page(state_dict)
    invoice = next(
        (inv for inv in page.items if inv.invoice.invoice_number == invoice_number),
        None,
    )

    if not invoice or not invoice.path:
        raise PreventUpdate

    LOG.info("Downloading from path: %s", invoice.path)

    try:
        workspace = clients.workspace_client()
        file_path = invoice.path

        workspace_path = file_path
        if file_path.startswith("dbfs:/"):
            workspace_path = file_path[5:]

        file_response = workspace.files.download(workspace_path)
        file_content = file_response.contents.read()

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
    """Entrypoint used by uv via `uv run invoice_ui`."""
    if USE_LIVE:
        configs.get()

    app.run(debug=True, host="0.0.0.0", port=APP_PORT, dev_tools_hot_reload=False)


if __name__ == "__main__":
    main()
