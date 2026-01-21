"""
Databricks Genie AI integration for natural language queries.

Provides a Service class for interacting with Databricks Genie spaces,
enabling natural language queries that return SQL and data.

This module wraps the Databricks SDK Genie API to provide a convenient
interface for sending messages and processing responses.
"""

import time
from dataclasses import dataclass
from typing import Any, Generator

from databricks.sdk import WorkspaceClient


def _get_attr(obj: Any, *attr_names: str) -> Any:
    """
    Get an attribute from an object, trying multiple attribute names.

    The Databricks SDK response objects may use different attribute names
    depending on the API version. This helper tries each name in order.
    The SDK's __getattr__ raises KeyError instead of AttributeError, so we
    need to catch both.

    Args:
        obj: Object to get attribute from.
        *attr_names: Attribute names to try in order.

    Returns:
        The first attribute value found.

    Raises:
        AttributeError: If none of the attribute names exist.
    """
    for name in attr_names:
        try:
            value = getattr(obj, name)
            if value is not None:
                return value
        except (KeyError, AttributeError):
            continue
    raise AttributeError(
        f"Object {type(obj).__name__} has none of attributes: {attr_names}"
    )


@dataclass
class GenieMessage:
    """
    Represents a message from Genie.

    Attributes:
        content: The text content of the message.
    """

    content: str | None = None


@dataclass
class GenieResponse:
    """
    Response from a Genie query.

    Wraps the raw SDK response to provide convenient access to status,
    messages, and SQL queries.

    Attributes:
        status_display: Human-readable status string.
        message: Optional message content from Genie.
    """

    status_display: str | None = None
    message: GenieMessage | None = None
    _attachments: list = None

    def __post_init__(self) -> None:
        if self._attachments is None:
            self._attachments = []

    def queries(self) -> list[str]:
        """
        Extract SQL queries from the response.

        Returns:
            List of SQL query strings from attachments.
        """
        sql_queries = []
        for attachment in self._attachments:
            if hasattr(attachment, "query") and attachment.query:
                query_obj = attachment.query
                if hasattr(query_obj, "query") and query_obj.query:
                    sql_queries.append(query_obj.query)
        return sql_queries


@dataclass
class ConversationInfo:
    """
    Information about a Genie conversation.

    Attributes:
        conversation_id: Unique identifier for the conversation.
    """

    conversation_id: str


class Service:
    """
    Service for interacting with a Databricks Genie space.

    Handles conversation management and message execution with
    polling for completion.

    Attributes:
        workspace_client: Databricks WorkspaceClient instance.
        space_id: The Genie space ID to interact with.
    """

    # Poll interval for checking message completion
    _POLL_INTERVAL = 1.0
    # Maximum time to wait for a message to complete
    _MAX_WAIT_TIME = 300.0

    def __init__(self, workspace_client: WorkspaceClient, space_id: str) -> None:
        """
        Initialize the Genie service.

        Args:
            workspace_client: Configured WorkspaceClient instance.
            space_id: The Genie space ID to use for queries.
        """
        self.workspace_client = workspace_client
        self.space_id = space_id

    def create_conversation(self, title: str | None = None) -> ConversationInfo:
        """
        Create a new conversation in the Genie space.

        Args:
            title: Optional title/context for the conversation.

        Returns:
            ConversationInfo with the conversation_id.
        """
        response = self.workspace_client.genie.start_conversation(
            space_id=self.space_id,
            content=title or "New conversation",
        )
        # Extract conversation_id - SDK may use different attribute names
        conv_id = _get_attr(response, "conversation_id", "id")
        return ConversationInfo(conversation_id=conv_id)

    def chat(
        self, conversation_id: str, message: str
    ) -> Generator[GenieResponse, None, None]:
        """
        Send a message and yield responses as they become available.

        This is a generator that polls for completion and yields
        GenieResponse objects with status updates and final results.

        Args:
            conversation_id: The conversation to send the message to.
            message: The natural language query.

        Yields:
            GenieResponse objects with status updates and results.
        """
        # Start the message
        msg_response = self.workspace_client.genie.create_message(
            space_id=self.space_id,
            conversation_id=conversation_id,
            content=message,
        )

        # Extract message_id - SDK may use different attribute names
        message_id = _get_attr(msg_response, "message_id", "id")

        # Poll for completion
        start_time = time.time()
        last_status = None

        while time.time() - start_time < self._MAX_WAIT_TIME:
            result = self.workspace_client.genie.get_message(
                space_id=self.space_id,
                conversation_id=conversation_id,
                message_id=message_id,
            )

            status = getattr(result, "status", None)
            status_str = str(status).replace("MessageStatus.", "") if status else None

            # Yield status update if changed
            if status_str != last_status:
                last_status = status_str
                yield GenieResponse(
                    status_display=self._format_status(status_str),
                    message=None,
                    _attachments=[],
                )

            # Check if completed
            if status_str in ("COMPLETED", "FAILED", "CANCELLED"):
                break

            time.sleep(self._POLL_INTERVAL)

        # Get the final result
        final_result = self.workspace_client.genie.get_message(
            space_id=self.space_id,
            conversation_id=conversation_id,
            message_id=message_id,
        )

        # Extract attachments (contain SQL queries)
        attachments = getattr(final_result, "attachments", []) or []

        # Extract message content
        content = getattr(final_result, "content", None)
        genie_message = GenieMessage(content=content) if content else None

        yield GenieResponse(
            status_display=self._format_status(last_status or "COMPLETED"),
            message=genie_message,
            _attachments=attachments,
        )

    def _format_status(self, status: str | None) -> str:
        """
        Format a status string for display.

        Args:
            status: Raw status string from the API.

        Returns:
            Human-readable status string.
        """
        status_map = {
            "SUBMITTED": "Submitted",
            "FILTERING_CONTEXT": "Filtering context...",
            "ASKING_AI": "Asking AI...",
            "EXECUTING_QUERY": "Executing query...",
            "COMPLETED": "Completed",
            "FAILED": "Failed",
            "CANCELLED": "Cancelled",
        }
        return status_map.get(status, status or "Processing...")
