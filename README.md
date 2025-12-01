
# Invoice Search UI (Dash)

This repository now hosts a Dash application that recreates the original React design for exploring computer hardware invoices. The layout, typography, and card structure closely follow the reference UI while using a Python stack.

## Prerequisites

1. Install [uv](https://docs.astral.sh/uv/) for fast Python environment management.
2. Ensure Python 3.11 or newer is available on your system.

## Setup and Development

1. Install dependencies into a local virtual environment:
   ```
   uv sync
   ```
2. Start the Dash development server:
   ```
   uv run invoice_ui
   ```
   The app listens on http://127.0.0.1:8050 by default.
3. Use the same command in production contexts or wrap it with a process manager of your choice.

## Service Abstraction

All data access flows through `invoice_ui.services.InvoiceService`. The default `DemoInvoiceService` exposes the static data that shipped with the React app, but you can swap in another backend:

1. Implement a class that inherits `InvoiceService` and register it in `invoice_ui/services/__init__.py`.
2. Set the `INVOICE_UI_SERVICE` environment variable to the registered key before launching the app.

This separation keeps callbacks and Dash components focused on presentation while backend integrations remain isolated.
  