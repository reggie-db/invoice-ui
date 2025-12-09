"""
Infinite scroll component wrapper for react-infinite-scroll-component.

Provides automatic loading of more content when user scrolls to the bottom.
"""

import reflex as rx


class InfiniteScroll(rx.NoSSRComponent):
    """Wrapper for react-infinite-scroll-component."""

    library = "react-infinite-scroll-component"
    tag = "InfiniteScroll"
    is_default = True

    data_length: int
    next: rx.EventHandler
    has_more: bool

    loader: rx.Component | None = None
    end_message: rx.Component | None = None
    scrollable_target: str | None = None
