
# Invoice Search UI

Invoice Search UI is a Dash web application for browsing hardware invoices by invoice number, PO, customer, or item details. It reproduces a polished card-based design, supports infinite scroll, and can source its data from either bundled demo invoices or a live backend service.

## Features

- Rich invoice cards with seller/buyer/ship-to summaries, line-item breakdowns, and serial number badges.
- Debounced search that filters across invoice metadata, company names, part numbers, and serial numbers.
- Infinite scrolling results list with lazy loading for large datasets.
- Swappable data services so the UI can point to mock data or a production-grade provider.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for environment management

## Getting Started

```bash
uv sync          # install dependencies into .venv
uv run invoice_ui
```

Visit http://127.0.0.1:8050/ to use the UI. The app reloads automatically when Python files or assets change.

## Data Services

All data flows through `invoice_ui.services.InvoiceService`. Two implementations are included:

- `demo`: ships with curated invoice fixtures.
- `impl`: fetches JSON invoices from a Spark table via `reggie_tools`.

Switch between services by setting `INVOICE_UI_SERVICE=demo` (default) or `INVOICE_UI_SERVICE=impl`. Any custom provider can plug in by subclassing `InvoiceService`, registering it in `invoice_ui/services/__init__.py`, and pointing the environment variable at the new key.
  