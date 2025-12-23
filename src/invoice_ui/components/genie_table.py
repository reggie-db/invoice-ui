"""
Genie table component for displaying AI query results.

When Databricks Genie returns data that doesn't include content_hash values
(meaning it can't filter invoices directly), the results are displayed in
an interactive AG Grid table with:

- Sortable and filterable columns
- Pagination for large result sets
- CSV export functionality
- SQL syntax highlighting for the generated query

Components:
- build_genie_table(): Full table display with header, grid, and query
- build_genie_query_details(): Collapsible SQL query card (used when invoices shown)
- build_sql_code_block(): Syntax-highlighted SQL code block
"""

import dash_ag_grid as dag
from dash import html
from dash_iconify import DashIconify

from invoice_ui.models.common import GenieTableResult


def build_sql_code_block(sql: str) -> html.Div:
    """
    Build a SQL code block with syntax highlighting.

    Uses highlight.js for ANSI SQL syntax highlighting.

    Args:
        sql: The SQL query string.

    Returns:
        A Div containing the highlighted SQL code.
    """
    return html.Div(
        className="sql-code-container",
        children=[
            html.Pre(
                html.Code(
                    sql,
                    className="language-sql",
                ),
                className="sql-code-block",
            ),
        ],
    )


def build_genie_query_details(genie_table: GenieTableResult) -> html.Div:
    """
    Build a collapsible component showing just the Genie SQL query.

    Used when content_hash filtering is applied and invoices are displayed.

    Args:
        genie_table: The Genie result containing the query.

    Returns:
        A Div containing the collapsible query details.
    """
    if not genie_table or not genie_table.query:
        return html.Div()

    return html.Div(
        className="genie-query-card",
        children=[
            html.Details(
                className="genie-query-details-card",
                children=[
                    html.Summary(
                        children=[
                            DashIconify(
                                icon="lucide:sparkles", className="genie-summary-icon"
                            ),
                            html.Span("AI Generated Query"),
                            html.Span(
                                f"({len(genie_table.rows)} results)"
                                if genie_table.rows
                                else "",
                                className="genie-result-count",
                            ),
                        ],
                    ),
                    html.Div(
                        className="genie-query-content",
                        children=[
                            html.P(
                                genie_table.description,
                                className="genie-description",
                            )
                            if genie_table.description
                            else None,
                            build_sql_code_block(genie_table.query),
                        ],
                    ),
                ],
            ),
        ],
    )


def build_genie_table(genie_table: GenieTableResult, query: str | None) -> html.Div:
    """
    Build a table component displaying Genie query results using AG Grid.

    Provides sortable, filterable columns with CSV/Excel export capability.

    Args:
        genie_table: The Genie table result with columns and rows.
        query: The original search query.

    Returns:
        A Div containing the AG Grid table and query details.
    """
    if not genie_table or not genie_table.rows:
        return html.Div()

    return html.Div(
        className="genie-table-container",
        children=[
            _build_header(genie_table, query),
            _build_ag_grid_table(genie_table),
            _build_query_section(genie_table),
        ],
    )


def _build_header(genie_table: GenieTableResult, query: str | None) -> html.Div:
    """Build the header section with icon and description."""
    children = [
        html.Div(
            className="genie-table-header",
            children=[
                DashIconify(icon="lucide:sparkles", className="genie-icon"),
                html.H3("AI Query Results"),
            ],
        ),
    ]

    # Only show description if it's meaningfully different from the query
    description = genie_table.description
    if description and query:
        # Skip description if it's essentially the same as the query
        if description.strip().lower() == query.strip().lower():
            description = None

    if description:
        children.append(
            html.P(
                description,
                className="genie-description",
            )
        )

    children.append(
        html.P(
            f"Showing {len(genie_table.rows)} row{'s' if len(genie_table.rows) != 1 else ''}",
            className="muted",
        )
    )

    return html.Div(className="genie-table-info", children=children)


def _build_ag_grid_table(genie_table: GenieTableResult) -> html.Div:
    """Build the AG Grid table with export functionality."""
    # Build column definitions
    column_defs = [
        {
            "field": col,
            "headerName": _format_column_name(col),
            "sortable": True,
            "filter": True,
            "resizable": True,
            "minWidth": 100,
        }
        for col in genie_table.columns
    ]

    # Format row data
    row_data = [
        {col: _format_cell_value(row.get(col)) for col in genie_table.columns}
        for row in genie_table.rows
    ]

    return html.Div(
        className="genie-grid-wrapper",
        children=[
            dag.AgGrid(
                id="genie-results-grid",
                columnDefs=column_defs,
                rowData=row_data,
                defaultColDef={
                    "flex": 1,
                    "minWidth": 100,
                    "sortable": True,
                    "filter": True,
                    "resizable": True,
                },
                dashGridOptions={
                    "pagination": True,
                    "paginationPageSize": 20,
                    "paginationPageSizeSelector": [10, 20, 50, 100],
                    "domLayout": "autoHeight",
                    "enableCellTextSelection": True,
                    "ensureDomOrder": True,
                },
                csvExportParams={
                    "fileName": "genie_results.csv",
                },
                className="ag-theme-alpine genie-ag-grid",
                style={"width": "100%"},
            ),
            html.Div(
                className="genie-export-buttons",
                children=[
                    html.Button(
                        children=[
                            DashIconify(icon="lucide:download", width=16),
                            " Export CSV",
                        ],
                        id="genie-export-csv-btn",
                        className="export-button",
                        n_clicks=0,
                    ),
                ],
            ),
        ],
    )


def _build_query_section(genie_table: GenieTableResult) -> html.Div:
    """Build the SQL query section with syntax highlighting."""
    if not genie_table.query:
        return html.Div()

    return html.Details(
        className="genie-query-details",
        children=[
            html.Summary(
                children=[
                    DashIconify(icon="lucide:code", width=16),
                    " View SQL Query",
                ],
            ),
            html.Div(
                className="genie-query-section-content",
                children=[
                    build_sql_code_block(genie_table.query),
                ],
            ),
        ],
    )


def _format_column_name(column: str) -> str:
    """
    Format a column name for display in AG Grid header.

    Converts snake_case to Title Case for better readability.

    Args:
        column: Raw column name from DataFrame.

    Returns:
        Human-readable column header string.
    """
    return column.replace("_", " ").title()


def _format_cell_value(value) -> str:
    """
    Format a cell value for display in AG Grid.

    Handles None, floats (with thousand separators), and complex types.

    Args:
        value: Raw cell value from DataFrame row.

    Returns:
        String representation suitable for display.
    """
    if value is None:
        return ""
    if isinstance(value, float):
        # Format whole numbers without decimals, others with 2 decimal places
        if value == int(value):
            return str(int(value))
        return f"{value:,.2f}"
    if isinstance(value, (list, dict)):
        return str(value)
    return str(value)
