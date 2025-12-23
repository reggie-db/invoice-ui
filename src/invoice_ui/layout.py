"""
Layout helpers for the Invoice Search Dash application.

This module defines the root layout structure including:
- URL tracking for hash-based routing
- dcc.Store components for state management
- WebSocket connection for Genie status updates
- Search panel and results container

The layout supports both generic and branded modes controlled by
the INVOICE_UI_GENERIC environment variable.
"""

import os

from dash import dcc, html
from dash_extensions import WebSocket

from invoice_ui.components.invoice_results import build_loading_state
from invoice_ui.components.invoice_search import build_search_panel

# Branding configuration
_USE_GENERIC = os.getenv("INVOICE_UI_GENERIC", "false").lower() in {"1", "true", "yes"}

_BRANDING = {
    "title": "Invoice Search" if _USE_GENERIC else "Hardware Invoice Search",
    "subtitle": (
        "Search and browse invoices."
        if _USE_GENERIC
        else "Search through computer hardware orders and invoices."
    ),
}

# WebSocket path (same port as app)
_WS_PATH = "/ws/genie"


def build_layout(ai_available: bool = False) -> html.Div:
    """
    Build the root layout for the Invoice Search application.

    Creates the complete Dash layout including:
    - Hidden state stores (dcc.Store) for application state management
    - WebSocket component for real-time Genie status updates
    - Page header with branding
    - Search panel with optional AI toggle
    - Results container (initially shows loading state)

    The layout renders immediately with a loading indicator. Invoice data
    is fetched asynchronously via the update_invoice_state callback triggered
    by initial-load-trigger.

    Args:
        ai_available: If True, shows the AI search toggle button.

    Returns:
        Root html.Div containing the complete application layout.
    """
    return html.Div(
        className="app-shell",
        children=[
            # URL tracking for hash-based state (search query in fragment)
            dcc.Location(id="url", refresh=False),
            # Download component for PDF exports
            dcc.Download(id="download-file"),
            # Main application state store (serialized AppState)
            dcc.Store(id="invoice-state", data=None),
            # Counter incremented by scroll events to trigger pagination
            dcc.Store(id="scroll-trigger", data=0),
            # Stores DBFS path for pending download
            dcc.Store(id="download-path-store", data=""),
            # Timestamp trigger for download callback
            dcc.Store(id="download-trigger", data=0),
            # Set to 1 to trigger initial data load on app mount
            dcc.Store(id="initial-load-trigger", data=1),
            # WebSocket URL configuration (path resolved relative to host)
            dcc.Store(id="ws-url-store", data={"path": _WS_PATH}),
            # WebSocket connection for Genie AI status updates
            WebSocket(id="genie-ws", url=""),
            # Hidden button target for AG Grid CSV export callback
            html.Button(
                id="genie-export-csv-btn",
                style={"display": "none"},
                n_clicks=0,
            ),
            html.Div(
                className="app-container",
                children=[
                    _build_page_header(),
                    build_search_panel("", ai_available=ai_available),
                    html.Div(
                        id="results-container",
                        children=build_loading_state(),
                    ),
                ],
            ),
        ],
    )


def _build_page_header() -> html.Div:
    """Return the hero text area at the top of the page."""
    return html.Div(
        className="page-header",
        children=[
            html.H1(_BRANDING["title"]),
            html.P(_BRANDING["subtitle"]),
        ],
    )
