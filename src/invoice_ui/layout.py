from dash import dcc, html

from invoice_ui.components.invoice_results import build_invoice_results
from invoice_ui.components.invoice_search import build_search_panel
from invoice_ui.components.vaadin_grid.vaadin_grid import VaadinGrid
from invoice_ui.models.invoice import InvoicePage, serialize_page

GRID_COLUMNS = [
    {"path": "id", "header": "ID"},
    {"path": "name", "header": "Name"},
    {"path": "email", "header": "Email"},
    {"path": "department", "header": "Department"},
    {"path": "status", "header": "Status"},
]

"""Layout helpers for the Dash app."""


def build_layout(initial_page: InvoicePage, initial_query: str = "") -> html.Div:
    """Return the root layout for the app."""
    initial_state = serialize_page(initial_page, initial_query, scroll_token=0)
    return html.Div(
        className="app-shell",
        children=[
            dcc.Location(id="url", refresh=False),
            dcc.Download(id="download-file"),
            dcc.Store(id="invoice-state", data=initial_state),
            dcc.Store(id="scroll-trigger", data=0),
            html.Div(
                className="app-container",
                children=[
                    _build_page_header(),
                    dcc.Tabs(
                        id="app-tabs",
                        value="search-tab",
                        className="app-tabs",
                        children=[
                            dcc.Tab(
                                label="Invoice Search",
                                value="search-tab",
                                className="app-tab",
                                selected_className="app-tab--selected",
                            ),
                            dcc.Tab(
                                label="Data Grid",
                                value="grid-tab",
                                className="app-tab",
                                selected_className="app-tab--selected",
                            ),
                        ],
                    ),
                    # Render search tab initially so search-query exists
                    html.Div(
                        id="tab-content",
                        children=build_search_tab(initial_page, initial_query),
                    ),
                ],
            ),
        ],
    )


def build_search_tab(initial_page: InvoicePage, initial_query: str) -> html.Div:
    """Return the search tab content."""
    return html.Div(
        children=[
            build_search_panel(initial_query),
            html.Div(
                id="results-container",
                children=build_invoice_results(
                    initial_page, initial_query, initial_page.has_more
                ),
            ),
        ]
    )


def build_grid_tab() -> html.Div:
    """Return the Vaadin Grid tab content."""
    return html.Div(
        className="grid-tab-content",
        children=[
            dcc.Store(id="grid-data-store", data=[]),
            html.Div(
                className="card",
                children=[
                    html.H3("Vaadin Grid Demo (1000 rows)", className="grid-title"),
                    html.P(
                        "Server-side data loading with Vaadin React Components",
                        className="muted",
                    ),
                    html.Div(
                        className="vaadin-grid-wrapper",
                        children=[
                            VaadinGrid(
                                id="vaadin-grid",
                                columns=GRID_COLUMNS,
                                totalCount=1000,
                            ),
                        ],
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
            html.H1("Hardware Invoice Search"),
            html.P("Search through computer hardware orders and invoices."),
        ],
    )
