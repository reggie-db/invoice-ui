from __future__ import annotations

from typing import Sequence

from dash import html

from invoice_ui.components.invoice_results import build_invoice_results
from invoice_ui.components.invoice_search import build_search_panel
from invoice_ui.models.invoice import Invoice

"""Layout helpers for the Dash app."""


def build_layout(initial_invoices: Sequence[Invoice], initial_query: str = "") -> html.Div:
    """Return the root layout for the app."""
    return html.Div(
        className="app-shell",
        children=[
            html.Div(
                className="app-container",
                children=[
                    _build_page_header(),
                    build_search_panel(initial_query),
                    html.Div(
                        id="results-container",
                        children=build_invoice_results(initial_invoices, initial_query),
                    ),
                ],
            )
        ],
    )


def _build_page_header() -> html.Div:
    """Return the hero text area at the top of the page."""
    return html.Div(
        className="page-header",
        children=[
            html.H1("Hardware Invoice Search"),
            html.P("Search through computer hardware orders and invoices."),
        ],
    )

