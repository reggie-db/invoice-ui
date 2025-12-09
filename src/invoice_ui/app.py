"""
Reflex application entry point for the Invoice Search UI.

This module initializes the Reflex app and defines the main page layout.
"""

import os

import reflex as rx
from reggie_core import logs

from invoice_ui.components.results import invoice_results
from invoice_ui.components.search_panel import search_panel
from invoice_ui.state import APP_SUBTITLE, APP_TITLE, InvoiceState

LOG = logs.logger(__file__)

# Configuration from environment
APP_PORT = int(os.getenv("DATABRICKS_APP_PORT", "8000"))
USE_GENERIC_BRANDING = os.getenv("INVOICE_UI_GENERIC", "false").lower() in {
    "1",
    "true",
    "yes",
}

# Configure invoice table name
_INVOICE_TABLE_NAME_KEY = "INVOICE_TABLE_NAME"
_DEFAULT_INVOICE_TABLE_NAME = "reggie_pierce.invoice_pipeline_dev.info_parse"
if not os.environ.get(_INVOICE_TABLE_NAME_KEY, None):
    os.environ[_INVOICE_TABLE_NAME_KEY] = _DEFAULT_INVOICE_TABLE_NAME
_INVOICE_TABLE_NAME = os.environ[_INVOICE_TABLE_NAME_KEY]
LOG.info("%s: %s", _INVOICE_TABLE_NAME_KEY, _INVOICE_TABLE_NAME)

# Configure genie space id
_INVOICE_GENIE_SPACE_ID_KEY = "INVOICE_GENIE_SPACE_ID"
if _INVOICE_TABLE_NAME == _DEFAULT_INVOICE_TABLE_NAME:
    if not os.environ.get(_INVOICE_GENIE_SPACE_ID_KEY, None):
        os.environ[_INVOICE_GENIE_SPACE_ID_KEY] = "01f0cfa53c571bbb9b36f0e14a4e408d"
LOG.info(
    "%s: %s",
    _INVOICE_GENIE_SPACE_ID_KEY,
    os.environ.get(_INVOICE_GENIE_SPACE_ID_KEY, None),
)
# Font URLs for theming
_FONT_URL_GENERIC = "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap"
_FONT_URL_BRANDED = "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Source+Sans+3:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap"
_FONT_URL = _FONT_URL_GENERIC if USE_GENERIC_BRANDING else _FONT_URL_BRANDED

# Theme class for body
_THEME_CLASS = "theme-generic" if USE_GENERIC_BRANDING else ""


def page_header() -> rx.Component:
    """Build the hero text area at the top of the page."""
    return rx.box(
        rx.heading(APP_TITLE, size="6", as_="h1"),
        rx.text(APP_SUBTITLE, class_name="muted"),
        class_name="page-header",
    )


def index() -> rx.Component:
    """
    Build the main page layout.

    Returns:
        The complete page component with header, search, and results.
    """
    return rx.box(
        rx.box(
            page_header(),
            search_panel(),
            invoice_results(),
            class_name="app-container",
        ),
        class_name="app-shell",
        on_mount=InvoiceState.load_more,
    )


# Create the Reflex app
app = rx.App(
    theme=rx.theme(
        appearance="light",
        has_background=True,
        radius="large",
    ),
    stylesheets=[
        _FONT_URL,
        "/styles.css",
    ],
)

# Add the index page
app.add_page(
    index,
    title=APP_TITLE,
    on_load=InvoiceState.on_load,
)


def main() -> None:
    """Entrypoint used by uv via `uv run invoice_ui`."""
    # Note: In production, use `reflex run` instead
    # This is kept for backwards compatibility
    import subprocess
    import sys

    subprocess.run([sys.executable, "-m", "reflex", "run", "--port", str(APP_PORT)])


if __name__ == "__main__":
    main()
