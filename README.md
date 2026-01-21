# Invoice Search UI

A Dash web application for browsing and searching hardware invoices with optional AI-powered semantic search via Databricks Genie. Designed to run as a [Databricks App](https://docs.databricks.com/en/dev-tools/databricks-apps/index.html) with real-time status updates over WebSocket.

## Features

- **Rich Invoice Cards**: Display seller/buyer/ship-to summaries, line-item breakdowns, and serial number badges
- **Flexible Search**: Filter by invoice number, PO number, serial number, company name, or any invoice metadata
- **AI-Powered Search**: Leverage Databricks Genie to answer natural language queries about invoices
- **Infinite Scroll**: Lazy loading for large datasets with smooth pagination
- **Real-Time Status**: WebSocket integration shows Genie AI processing status in real-time
- **PDF Downloads**: Download invoice PDFs directly from DBFS or Unity Catalog volumes
- **Shareable URLs**: Search queries sync to URL fragments for easy sharing
- **AG Grid Results**: When Genie returns non-invoice data, results display in a sortable/exportable table

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for environment management
- Databricks workspace (for production/Spark-backed mode)
- Optional: Genie AI space configured for natural language search

## Quick Start

```bash
# Install dependencies
uv sync

# Run in demo mode (no Databricks connection required)
INVOICE_UI_USE_LIVE=false uv run invoice_ui

# Run in production mode (requires Databricks)
uv run invoice_ui
```

Visit http://0.0.0.0:8000/ to use the UI. The default port is `8000` (configurable via `DATABRICKS_APP_PORT`).

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `INVOICE_UI_USE_LIVE` | `true` | Set to `false` for demo mode with static data |
| `INVOICE_UI_SERVICE` | `impl` | Service implementation: `impl` (Spark) or `demo` |
| `INVOICE_UI_GENERIC` | `false` | Use generic branding instead of "Hardware Invoice" |
| `DATABRICKS_APP_PORT` | `8000` | Port for the web server |
| `INVOICE_TABLE_NAME` | (required in prod) | Unity Catalog table containing invoice JSON data |
| `INVOICE_GENIE_SPACE_ID` | (optional) | Genie space ID for AI-powered search |

### Invoice Table Schema

The production service expects a Unity Catalog table with the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `content_hash` | STRING | Unique identifier for each invoice document |
| `value` | STRUCT | Nested JSON structure containing invoice data |
| `path` | STRING | DBFS/Volumes path to the source PDF file |

The `value` struct should contain:
- `invoice`: Invoice metadata (number, dates, amounts, terms)
- `buyer`, `seller`, `shipTo`: Party information
- `lineItems`: Array of line items with quantities, prices, serial numbers
- `totals`: Subtotal, tax, shipping, and total amounts

### Genie AI Setup

To enable AI-powered natural language search:

1. Create a Genie space in your Databricks workspace
2. Add your invoice table to the Genie space
3. Configure the space to understand invoice queries
4. Set `INVOICE_GENIE_SPACE_ID` to your space ID

Genie queries that return a `content_hash` column filter invoices directly. Queries returning other data display in an AG Grid table with export capabilities.

## Architecture

```
invoice-ui/
├── src/invoice_ui/
│   ├── app.py              # Dash app entry point, callbacks, WebSocket init
│   ├── layout.py           # Root layout builder
│   ├── utils.py            # Formatting and filtering helpers
│   ├── ws_server.py        # WebSocket server for Genie status broadcasts
│   ├── components/         # Reusable Dash UI components
│   │   ├── genie_table.py      # AG Grid for Genie query results
│   │   ├── invoice_card.py     # Invoice detail card
│   │   ├── invoice_results.py  # Results list with infinite scroll
│   │   └── invoice_search.py   # Search input with AI toggle
│   ├── models/             # Data models and serialization
│   │   ├── common.py           # Shared state models (AppState, GenieTableResult)
│   │   └── invoice.py          # Invoice dataclasses and (de)serialization
│   ├── services/           # Data access layer
│   │   ├── invoice_service.py      # Abstract base class
│   │   ├── invoice_service_impl.py # Spark/Genie implementation
│   │   └── invoice_service_demo.py # In-memory demo implementation
│   └── data/               # Static demo data
│       └── demo_invoices.py
├── assets/                 # Static CSS and JavaScript
│   ├── styles.css              # Main stylesheet with AG Grid theming
│   └── hash-router-handler.js  # URL fragment sync for search state
├── run.sh                  # Databricks App entry script
├── app.yaml                # Databricks App configuration
└── pyproject.toml          # Project dependencies and build config
```

### Data Flow

1. **Search Input**: User types query or toggles AI search
2. **URL Sync**: Query is base64-encoded to URL fragment for shareability
3. **Callback**: Dash callback triggers `InvoiceService.list_invoices()`
4. **AI Path** (if enabled):
   - Query sent to Genie via local genie module (using databricks-sdk)
   - Status updates broadcast over WebSocket
   - Genie returns SQL query executed against invoice table
   - If `content_hash` found, invoices are filtered
   - Otherwise, raw table data displayed in AG Grid
5. **Fallback Path**: Plain text search against serialized invoice JSON
6. **Render**: Invoice cards or Genie table displayed with pagination

### WebSocket Integration

Real-time Genie status updates use `flask-sock` to add WebSocket support to the Dash/Flask server:

- Endpoint: `/ws/genie`
- Messages: JSON-serialized `GenieStatusMessage` objects
- Client: `dash-extensions` WebSocket component

## Deployment

### Databricks Apps

The included `run.sh` and `app.yaml` support deployment as a Databricks App:

```yaml
# app.yaml
command:
  - ./run.sh
```

The `run.sh` script:
1. Installs `uv` if not present
2. Syncs dependencies
3. Runs the application

### Manual Deployment

For standalone deployment:

```bash
# Build wheel
uv build

# Install and run
pip install dist/invoice_ui-*.whl
invoice_ui
```

## Development

```bash
# Install dev dependencies
uv sync --all-extras

# Run with hot reload (disabled by default for stability)
uv run invoice_ui

# Run linting
uv run ruff check src/

# Run tests
uv run pytest
```

### Adding Custom Services

1. Create a new class extending `InvoiceService`
2. Implement `list_invoices()` method
3. Register in `services/__init__.py`:

```python
_SERVICE_REGISTRY["my_service"] = lambda: MyInvoiceService()
```

4. Set `INVOICE_UI_SERVICE=my_service`

## Dependencies

### Core
- **Dash**: Web framework for Python
- **dash-ag-grid**: AG Grid integration for tabular data
- **dash-extensions**: WebSocket support
- **dash-iconify**: Icon components
- **flask-sock**: WebSocket server for Flask

### Databricks Integration
- **databricks-sdk**: Databricks SDK for Genie AI and Workspace API
- **databricks-connect**: Spark connectivity for Databricks environments
- **pyspark**: Apache Spark for data processing
- **diskcache**: Disk-based caching with TTL support
- **python-benedict**: Nested dictionary access

## License

See [LICENSE](LICENSE) file.
