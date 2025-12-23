"""
Invoice search panel component.

Provides the search input with:
- Icon-prefixed text input with debounce
- Optional AI toggle button (when Genie is configured)
- Real-time Genie status indicator (hidden by default)

The search input uses Dash's debounce feature to avoid excessive
server callbacks while the user types.
"""

from dash import dcc, html
from dash_iconify import DashIconify


def build_search_panel(initial_value: str = "", ai_available: bool = False) -> html.Div:
    """
    Build the search panel with input and optional AI toggle.

    Args:
        initial_value: Pre-populated search query (from URL hash).
        ai_available: If True, shows the AI search toggle button.

    Returns:
        Card-styled div containing the search UI elements.
    """
    input_children = [
        DashIconify(icon="lucide:search", className="input-icon"),
        dcc.Input(
            id="search-query",
            type="text",
            value=initial_value,
            placeholder="Search by invoice number, PO number, serial number, company name...",
            className="search-input",
            debounce=True,
        ),
    ]

    # Add AI toggle button inline with search input
    if ai_available:
        input_children.append(
            html.Div(
                className="ai-toggle-wrapper",
                title="Enable/Disable AI Search",
                children=[
                    dcc.Checklist(
                        id="ai-search-toggle",
                        options=[
                            {
                                "label": html.Span(
                                    className="ai-toggle-button",
                                    children=[
                                        DashIconify(
                                            icon="lucide:sparkles",
                                            className="ai-toggle-icon",
                                        ),
                                    ],
                                ),
                                "value": "enabled",
                            }
                        ],
                        value=["enabled"],  # Default enabled
                        className="ai-toggle-checklist",
                    ),
                ],
            )
        )

    children = [
        html.Div(className="input-with-icon", children=input_children),
        # Status indicator (updated via WebSocket)
        html.Div(
            id="genie-status",
            className="genie-status hidden",
            children=[
                html.Div(className="genie-spinner"),
                html.Div(
                    className="genie-status-content",
                    children=[
                        html.Span(
                            id="genie-status-text", className="genie-status-text"
                        ),
                        html.Span(
                            id="genie-status-message",
                            className="genie-status-message",
                        ),
                    ],
                ),
            ],
        ),
    ]

    return html.Div(className="card search-card", children=children)
