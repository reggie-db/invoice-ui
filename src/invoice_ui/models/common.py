from dataclasses import dataclass, field
from typing import Any

from reggie_tools import genie

"""
Common state models for the Invoice UI application.

These models are designed for reuse across different features and may
be shared with other applications in the future.
"""


@dataclass
class GenieTableResult:
    """
    Holds raw table data from a Genie query when no content_hash column is found.

    Attributes:
        columns: List of column names.
        rows: List of row dictionaries.
        query: The SQL query that was executed.
        description: Optional description from Genie about the results.
    """

    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    query: str = ""
    description: str = ""

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dictionary."""
        return {
            "columns": self.columns,
            "rows": self.rows,
            "query": self.query,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "GenieTableResult | None":
        """Deserialize from dictionary."""
        if not data:
            return None
        return cls(
            columns=data.get("columns", []),
            rows=data.get("rows", []),
            query=data.get("query", ""),
            description=data.get("description", ""),
        )


@dataclass
class PaginationState:
    """
    Tracks pagination state for any paginated list.

    Attributes:
        page: Current page number (1-indexed).
        page_size: Number of items per page.
        total: Total number of items available.
        has_more: Whether more pages are available.
    """

    page: int = 1
    page_size: int = 10
    total: int = 0
    has_more: bool = False

    def next_page(self) -> int:
        """Return the next page number."""
        return self.page + 1


@dataclass
class AppState:
    """
    Unified application state stored in dcc.Store.

    All UI state flows through this dataclass for type safety.
    Genie status is intentionally excluded as it's managed via
    WebSocket with real-time progress updates.

    Attributes:
        items: Serialized list of items (invoice dicts).
        pagination: Current pagination state.
        query: Current search query string.
        scroll_token: Token to track scroll-based loading.
        genie_table: Raw table results from Genie when no content_hash found.
    """

    items: list[dict] = field(default_factory=list)
    pagination: PaginationState = field(default_factory=PaginationState)
    query: str = ""
    scroll_token: int = 0
    genie_table: GenieTableResult | None = None

    @property
    def page(self) -> int:
        """Current page number."""
        return self.pagination.page

    @property
    def page_size(self) -> int:
        """Items per page."""
        return self.pagination.page_size

    @property
    def total(self) -> int:
        """Total item count."""
        return self.pagination.total

    @property
    def has_more(self) -> bool:
        """Whether more pages exist."""
        return self.pagination.has_more

    @property
    def has_genie_table(self) -> bool:
        """Check if there are Genie table results to display."""
        return self.genie_table is not None and len(self.genie_table.rows) > 0

    def to_dict(self) -> dict:
        """Serialize state to JSON-compatible dictionary."""
        return {
            "items": self.items,
            "page": self.pagination.page,
            "page_size": self.pagination.page_size,
            "total": self.pagination.total,
            "has_more": self.pagination.has_more,
            "query": self.query,
            "scroll_token": self.scroll_token,
            "genie_table": self.genie_table.to_dict() if self.genie_table else None,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "AppState":
        """Deserialize dictionary to AppState."""
        if not data:
            return cls()
        return cls(
            items=data.get("items", []),
            pagination=PaginationState(
                page=data.get("page", 1),
                page_size=data.get("page_size", 10),
                total=data.get("total", 0),
                has_more=data.get("has_more", False),
            ),
            query=data.get("query", ""),
            scroll_token=data.get("scroll_token", 0),
            genie_table=GenieTableResult.from_dict(data.get("genie_table")),
        )


@dataclass
class GenieStatusMessage:
    """
    WebSocket message for Genie AI query status updates.

    This is sent via WebSocket, not stored in AppState.
    """

    active: bool = field(default=False)
    status: str | None = field(default=None)
    message: str | None = field(default=None)

    def to_dict(self) -> dict:
        """Serialize to JSON for WebSocket transmission."""
        return {
            "type": "genie_status",
            "active": self.active,
            "status": self.status,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GenieStatusMessage":
        """Deserialize from WebSocket message."""
        return cls(
            active=data.get("active", False),
            status=data.get("status"),
            message=data.get("message"),
        )

    @classmethod
    def from_response(
        cls, response: genie.GenieResponse | None
    ) -> "GenieStatusMessage":
        if response is None:
            return cls()
        return cls(
            active=True,
            status=response.status_display,
            message=cls._extract_genie_message(response),
        )

    @staticmethod
    def _extract_genie_message(response: genie.GenieResponse) -> str | None:
        """Extract display message from a Genie response."""
        if message := response.message:
            content = message.content.strip() if message.content else None
            if content:
                return content
        return None
