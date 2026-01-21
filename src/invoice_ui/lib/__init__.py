"""
Local library modules replacing external dbx-tools and dbx-concurio dependencies.

This package provides local implementations of utilities that were previously
imported from external Databricks utility packages. The goal is to reduce
external dependencies while maintaining the same functionality.

Modules:
    logs: Logging utilities
    objects: Object hashing and serialization
    paths: Path utilities
    clients: Databricks client factories (Spark, Workspace)
    genie: Databricks Genie AI integration
    caches: Disk-based caching with TTL support
"""

from invoice_ui.lib import caches, clients, genie, logs, objects, paths

__all__ = ["caches", "clients", "genie", "logs", "objects", "paths"]
