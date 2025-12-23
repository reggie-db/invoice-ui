"""
Common state models for the Invoice Search UI application.

This module defines shared state objects that are serialized to dcc.Store
for client-side persistence. These models handle:

- Application state (pagination, search query, cached items)
- Genie AI query results (SQL, table data, content hash filtering)
- WebSocket status messages for real-time updates

All models include to_dict/from_dict methods for JSON serialization
required by Dash's dcc.Store component.
"""

from dataclasses import dataclass, field
from typing import Any

from reggie_tools import genie


@dataclass
class GenieTableResult:
    """
    Holds Genie query information and optionally raw table data.

    Used both for:
    - Storing the SQL query when content_hash filtering is applied (rows empty)
    - Storing full table data when no content_hash column is found

    Attributes:
        columns: List of column names.
        rows: List of row dictionaries (empty when content_hash found).
        query: The SQL query that was executed.
        description: Optional description from Genie about the results.
        has_content_hash: True if the query returned content_hash for filtering.
    """

    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    query: str = ""
    description: str = ""
    has_content_hash: bool = False

    @property
    def has_table_data(self) -> bool:
        """Check if there is actual table data to display."""
        return len(self.rows) > 0

    @property
    def has_query(self) -> bool:
        """Check if there is a SQL query to display."""
        return bool(self.query)

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dictionary."""
        return {
            "columns": self.columns,
            "rows": self.rows,
            "query": self.query,
            "description": self.description,
            "has_content_hash": self.has_content_hash,
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
            has_content_hash=data.get("has_content_hash", False),
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
        return self.genie_table is not None and self.genie_table.has_table_data

    @property
    def has_genie_query(self) -> bool:
        """Check if there is a Genie SQL query to display."""
        return self.genie_table is not None and self.genie_table.has_query

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
