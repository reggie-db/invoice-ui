from dash import dcc, html
from dash_iconify import DashIconify

"""Invoice search input that mirrors the React design."""


def build_search_panel(initial_value: str = "", ai_available: bool = False) -> html.Div:
    """
    Return the search container with the query input.

    Args:
        initial_value: Pre-populated search query.
        ai_available: Whether AI-powered search is available (shows toggle if True).
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
