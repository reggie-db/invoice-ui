"""Reflex configuration for the Invoice UI application."""

import os

import reflex as rx

# Get port from environment
APP_PORT = int(os.getenv("DATABRICKS_APP_PORT", "8000"))

config = rx.Config(
    app_name="invoice_ui",
    # Use the src directory structure
    app_module_import="invoice_ui.app",
)

