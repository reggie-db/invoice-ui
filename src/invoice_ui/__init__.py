"""
Invoice Search UI: A Dash application for browsing hardware invoices.

This package provides a web interface for searching and viewing invoice
data stored in Databricks Unity Catalog, with optional AI-powered semantic
search via Databricks Genie.

Subpackages:
- components: Reusable Dash UI components
- models: Data models and serialization
- services: Data access layer (demo and production implementations)
- data: Static demo fixtures

Main entry points:
- app.main(): Start the development server
- app.app: The Dash application instance (for WSGI deployment)
"""

__all__ = ["__version__"]

__version__ = "0.1.0"

