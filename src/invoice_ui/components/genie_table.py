"""
Genie table component for displaying raw AI query results.

When Genie returns a query without content_hash column, the results
are displayed in this standard table format. When content_hash is found,
just the SQL query details are shown.
"""

from dash import html
from dash_iconify import DashIconify

from invoice_ui.models.common import GenieTableResult

"""Component for displaying Genie AI query results in a table format."""


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
                            DashIconify(icon="lucide:sparkles", className="genie-summary-icon"),
                            html.Span("AI Generated Query"),
                            html.Span(
                                f"({len(genie_table.rows)} results)" if genie_table.rows else "",
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
                            ) if genie_table.description else None,
                            html.Pre(
                                genie_table.query,
                                className="genie-sql",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def build_genie_table(genie_table: GenieTableResult, query: str | None) -> html.Div:
    """
    Build a table component displaying Genie query results.

    Args:
        genie_table: The Genie table result with columns and rows.
        query: The original search query.

    Returns:
        A Div containing the styled table.
    """
    if not genie_table or not genie_table.rows:
        return html.Div()

    return html.Div(
        className="genie-table-container",
        children=[
            _build_header(genie_table, query),
            _build_table(genie_table),
            _build_footer(genie_table),
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

    if query:
        children.append(
            html.P(
                f'Results for: "{query}"',
                className="genie-query-text",
            )
        )

    if genie_table.description:
        children.append(
            html.P(
                genie_table.description,
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


def _build_table(genie_table: GenieTableResult) -> html.Div:
    """Build the actual data table."""
    # Format column headers (convert snake_case to Title Case)
    formatted_columns = [
        _format_column_name(col) for col in genie_table.columns
    ]

    # Build table header
    thead = html.Thead(
        html.Tr([html.Th(col) for col in formatted_columns])
    )

    # Build table body
    tbody = html.Tbody([
        html.Tr([
            html.Td(_format_cell_value(row.get(col, "")))
            for col in genie_table.columns
        ])
        for row in genie_table.rows
    ])

    return html.Div(
        className="genie-table-wrapper",
        children=[
            html.Table(
                className="genie-table",
                children=[thead, tbody],
            )
        ],
    )


def _build_footer(genie_table: GenieTableResult) -> html.Div:
    """Build the footer with SQL query details."""
    if not genie_table.query:
        return html.Div()

    return html.Details(
        className="genie-query-details",
        children=[
            html.Summary("View SQL Query"),
            html.Pre(
                genie_table.query,
                className="genie-sql",
            ),
        ],
    )


def _format_column_name(column: str) -> str:
    """Format a column name for display (snake_case to Title Case)."""
    return column.replace("_", " ").title()


def _format_cell_value(value) -> str:
    """Format a cell value for display."""
    if value is None:
        return ""
    if isinstance(value, float):
        # Format numbers with reasonable precision
        if value == int(value):
            return str(int(value))
        return f"{value:,.2f}"
    if isinstance(value, (list, dict)):
        return str(value)
    return str(value)

