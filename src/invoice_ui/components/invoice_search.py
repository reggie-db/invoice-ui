from dash import dcc, html
from dash_iconify import DashIconify

"""Invoice search input that mirrors the React design."""


def build_search_panel(initial_value: str = "") -> html.Div:
    """
    Return the search container with the query input.

    Args:
        initial_value: Pre-populated search query.
    """
    return html.Div(
        className="card search-card",
        children=[
            html.Div(
                className="input-with-icon",
                children=[
                    DashIconify(icon="lucide:search", className="input-icon"),
                    dcc.Input(
                        id="search-query",
                        type="text",
                        value=initial_value,
                        placeholder="Search by invoice number, PO number, serial number, company name...",
                        className="search-input",
                        debounce=True,
                    ),
                ],
            ),
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
        ],
    )
