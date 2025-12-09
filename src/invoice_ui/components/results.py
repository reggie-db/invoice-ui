"""
Invoice results display component for Reflex.

Handles the display of search results, loading states, and empty states.
"""

import reflex as rx

from invoice_ui.components.infinite_scroll import InfiniteScroll
from invoice_ui.components.invoice_card_rx import invoice_card
from invoice_ui.state import InvoiceState


def invoice_results() -> rx.Component:
    """
    Build the invoice results container.

    Displays loading state, empty state, or invoice cards based on current state.

    Returns:
        The results container component.
    """

    return rx.box(
        rx.cond(
            InvoiceState.is_empty,
            _empty(),
            _results(),
        ),
        id="results-container",
    )


def _results() -> rx.Component:
    return rx.box(
        rx.cond(
            InvoiceState.total >= 0,
            rx.box(
                rx.text(InvoiceState.result_summary, class_name="muted"),
                class_name="results-summary",
            ),
            None,
        ),
        InfiniteScroll.create(
            rx.foreach(InvoiceState.invoices, invoice_card),
            data_length=InvoiceState.invoices.length(),
            next=InvoiceState.load_more,
            has_more=InvoiceState.has_more,
            loader=_loader(),
            end_message=_end_message(),
        ),
        class_name="results",
    )


def _empty() -> rx.Component:
    """Build the empty state when no invoices are found."""
    return rx.box(
        rx.icon("file-x", class_name="empty-icon", size=60),
        rx.heading("No invoices found", size="3", as_="h3"),
        rx.cond(
            InvoiceState.query != "",
            rx.text(
                rx.text.span('No results match "'),
                rx.text.span(InvoiceState.query),
                rx.text.span('". Try a different search term.'),
                class_name="muted",
            ),
            rx.text("No invoices available.", class_name="muted"),
        ),
        class_name="card empty-state",
    )


def _loader() -> rx.Component:
    """Build the loading indicator for initial page load."""
    return rx.box(
        rx.box(class_name="spinner"),
        rx.text("Loading invoices...", class_name="muted"),
        class_name="card loading-state",
    )


def _end_message() -> rx.Component:
    return rx.box(
        rx.text("All invoices loaded", class_name="load-more-hint end"),
        class_name="load-more-container",
    )
