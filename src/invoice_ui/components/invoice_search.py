from __future__ import annotations

from dash import dcc, html
from dash_iconify import DashIconify

"""Invoice search input that mirrors the React design."""


def build_search_panel(initial_value: str = "") -> html.Div:
    """Return the search container with the query input."""
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
            )
        ],
    )

