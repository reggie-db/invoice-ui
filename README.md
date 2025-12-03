  # Invoice Search UI

Invoice Search UI is a Dash web application for browsing hardware invoices by invoice number, PO, customer, or item details. It features a card-based design, infinite scroll, and can source data from bundled demo invoices or a live Spark-backed service.

## Features

- Rich invoice cards with seller/buyer/ship-to summaries, line-item breakdowns, and serial number badges
- Search filtering across invoice metadata, company names, part numbers, and serial numbers
- Infinite scrolling with lazy loading for large datasets
- Shareable search queries via URL fragments
- PDF download functionality for invoices
- Swappable data services supporting demo or production backends

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for environment management

## Getting Started

```bash
uv sync          # install dependencies into .venv
uv run invoice_ui
```

Visit http://0.0.0.0:8050/ to use the UI. The app reloads automatically when Python files or assets change.

## Data Services

All data flows through `invoice_ui.services.InvoiceService`. Two implementations are included:

- `demo`: ships with curated invoice fixtures for development and testing
- `impl`: fetches JSON invoices from a Spark table via `reggie_tools`

Switch between services using environment variables:
- `INVOICE_UI_SERVICE=demo` (default) or `INVOICE_UI_SERVICE=impl`
- `INVOICE_UI_USE_LIVE=true` (default) or `INVOICE_UI_USE_LIVE=false` to control live data usage

Any custom provider can plug in by subclassing `InvoiceService`, registering it in `invoice_ui/services/__init__.py`, and pointing the environment variable at the new key.

## Architecture

- **Models**: Dataclasses for invoice data (`invoice_ui.models.invoice`)
- **Services**: Abstract service interface with demo and Spark implementations (`invoice_ui.services`)
- **Components**: Reusable UI components for cards, search, and results (`invoice_ui.components`)
- **Utils**: Shared utilities for formatting and filtering (`invoice_ui.utils`)
- **Assets**: CSS and JavaScript files for styling and client-side behavior
  