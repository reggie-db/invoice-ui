"""
Search panel component for the Invoice UI.

Provides the search input with optional AI toggle button.
"""

import reflex as rx

from invoice_ui.state import InvoiceState


def search_panel() -> rx.Component:
    """
    Build the search panel with input and AI toggle.

    Returns:
        The search panel component.
    """
    return rx.box(
        rx.box(
            # Search icon
            rx.icon("search", class_name="input-icon"),
            # Search input
            rx.input(
                placeholder="Search by invoice number, PO number, serial number, company name...",
                value=InvoiceState.query,
                on_change=InvoiceState.search,
                class_name="search-input",
                debounce=300,
            ),
            # AI toggle button (conditionally rendered)
            rx.cond(
                InvoiceState.ai_available,
                rx.box(
                    rx.button(
                        rx.icon("sparkles", size=20),
                        on_click=InvoiceState.toggle_ai,
                        class_name=rx.cond(
                            InvoiceState.ai_enabled,
                            "ai-toggle-button active",
                            "ai-toggle-button",
                        ),
                        title="Toggle AI Search",
                    ),
                    class_name="ai-toggle-wrapper",
                ),
            ),
            class_name="input-with-icon",
        ),
        # Genie status indicator
        rx.cond(
            InvoiceState.genie_active,
            rx.box(
                rx.box(class_name="genie-spinner"),
                rx.box(
                    rx.text(InvoiceState.genie_status, class_name="genie-status-text"),
                    rx.text(
                        InvoiceState.genie_message, class_name="genie-status-message"
                    ),
                    class_name="genie-status-content",
                ),
                class_name="genie-status",
            ),
        ),
        class_name="card search-card",
    )

