from __future__ import annotations

from pathlib import Path

from dash import Dash, Input, Output

from invoice_ui.components.invoice_results import build_invoice_results
from invoice_ui.layout import build_layout
from invoice_ui.services import get_invoice_service

"""Dash application entry point."""

_service = get_invoice_service()
_initial_invoices = _service.all_invoices()
_assets_path = Path(__file__).resolve().parent.parent / "assets"

app = Dash(__name__, title="Hardware Invoice Search", assets_folder=str(_assets_path))
app.layout = build_layout(_initial_invoices)


@app.callback(Output("results-container", "children"), Input("search-query", "value"))
def filter_invoices(query: str | None) -> object:
    """Filter invoices whenever the user updates the query."""
    invoices = _service.search_invoices(query)
    return build_invoice_results(invoices, query)


def main() -> None:
    """Entrypoint used by uv via `uv run invoice_ui`."""
    app.run(debug=True, host="0.0.0.0", port=8050)


if __name__ == "__main__":
    main()

