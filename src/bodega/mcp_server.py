"""Bodega MCP Server - Model Context Protocol server implementation.

This module provides MCP tools for interacting with bodega tickets programmatically.
Uses zeromcp for the MCP protocol implementation and delegates to operations module
for business logic.
"""

import json
from typing import Annotated, Optional

from zeromcp import McpServer, McpToolError

from bodega.storage import TicketStorage
from bodega.config import BodegaConfig
from bodega.operations import (
    query_tickets,
    get_ready_tickets,
    create_ticket,
    start_ticket,
    close_ticket,
    add_note,
    add_dependency,
)
from bodega.output import ticket_to_dict, format_ticket_detail
from bodega.errors import TicketNotFoundError, AmbiguousIDError
from bodega.models.ticket import TicketStatus


# ============================================================================
# Server Factory
# ============================================================================

def create_mcp_server(storage: TicketStorage, config: BodegaConfig) -> McpServer:
    """Create and configure an MCP server instance.

    Args:
        storage: TicketStorage instance
        config: BodegaConfig instance

    Returns:
        Configured McpServer instance
    """
    mcp = McpServer("bodega")

    # ========================================================================
    # High Priority Tools - Core Workflow
    # ========================================================================

    @mcp.tool
    def bodega_query(
        ticket_id: Annotated[
            Optional[str],
            "Query single ticket by ID"
        ] = None,
        include_all: Annotated[bool, "Include closed tickets"] = False,
        status: Annotated[
            Optional[str],
            "Filter by status: open, in-progress, closed"
        ] = None,
        ticket_type: Annotated[
            Optional[str],
            "Filter by type: bug, feature, task, epic, chore"
        ] = None,
        tag: Annotated[Optional[str], "Filter by tag"] = None,
        assignee: Annotated[Optional[str], "Filter by assignee"] = None,
        priority: Annotated[
            Optional[int],
            "Filter by priority (0=critical, 1=high, 2=normal, 3=low, 4=backlog)"
        ] = None,
    ) -> str:
        """Query tickets as JSON for programmatic access."""
        try:
            status_filter = TicketStatus(status) if status else None
            result = query_tickets(
                storage,
                ticket_id=ticket_id,
                status=status_filter,
                ticket_type=ticket_type,
                tag=tag,
                assignee=assignee,
                priority=priority,
                include_closed=include_all,
            )

            # Single ticket or list
            if ticket_id:
                data = ticket_to_dict(result)
            else:
                data = [ticket_to_dict(t) for t in result]

            return json.dumps(data, indent=2, default=str)

        except TicketNotFoundError as e:
            raise McpToolError(str(e))
        except AmbiguousIDError as e:
            raise McpToolError(str(e))
        except ValueError as e:
            raise McpToolError(f"Invalid filter value: {e}")
        except Exception as e:
            raise McpToolError(f"Query failed: {e}")

    @mcp.tool
    def bodega_create(
        title: Annotated[str, "Ticket title"],
        ticket_type: Annotated[
            str,
            "Ticket type: bug, feature, task, epic, chore"
        ] = "task",
        priority: Annotated[
            Optional[int],
            "Priority (0=critical, 1=high, 2=normal, 3=low, 4=backlog)"
        ] = None,
        assignee: Annotated[Optional[str], "Assignee name"] = None,
        tags: Annotated[
            Optional[str],
            "Comma-separated tags (e.g. 'api,urgent')"
        ] = None,
        description: Annotated[Optional[str], "Ticket description"] = None,
        deps: Annotated[
            Optional[str],
            "Comma-separated blocking ticket IDs (e.g. 'bg-abc123,bg-def456')"
        ] = None,
        parent: Annotated[Optional[str], "Parent ticket ID (for epics)"] = None,
        external_ref: Annotated[
            Optional[str],
            "External reference (URL, issue number, etc.)"
        ] = None,
    ) -> str:
        """Create a new ticket with the specified properties and returns the ticket ID."""
        try:
            # Parse tags and deps
            tag_list = [t.strip() for t in tags.split(",")] if tags else None
            dep_list = [d.strip() for d in deps.split(",")] if deps else None

            ticket, missing_deps = create_ticket(
                storage,
                config,
                title=title,
                ticket_type=ticket_type,
                priority=priority,
                assignee=assignee,
                tags=tag_list,
                description=description,
                deps=dep_list,
                parent=parent,
                external_ref=external_ref,
            )

            # Include warning about missing dependencies in response
            if missing_deps:
                warning = f"Warning: Dependencies do not exist: {', '.join(missing_deps)}"
                return f"{ticket.id}\n{warning}"

            return ticket.id

        except ValueError as e:
            raise McpToolError(str(e))
        except Exception as e:
            raise McpToolError(f"Failed to create ticket: {e}")

    @mcp.tool
    def bodega_start(
        ticket_id: Annotated[
            str,
            "Ticket ID"
        ],
        assignee: Annotated[
            Optional[str],
            "Update assignee (defaults to git user if not set)"
        ] = None,
    ) -> str:
        """Set ticket status to in-progress."""
        try:
            ticket, already_in_progress = start_ticket(
                storage, config, ticket_id, assignee
            )

            if already_in_progress and assignee is None:
                return f"{ticket.id} is already in-progress"

            if already_in_progress:
                return f"Updated {ticket.id}"
            return f"{ticket.id} → in-progress"

        except TicketNotFoundError as e:
            raise McpToolError(str(e))
        except AmbiguousIDError as e:
            raise McpToolError(str(e))
        except Exception as e:
            raise McpToolError(f"Failed to start ticket: {e}")

    @mcp.tool
    def bodega_close(
        ticket_id: Annotated[str, "Ticket ID"],
    ) -> str:
        """Set ticket status to closed."""
        try:
            ticket, already_closed = close_ticket(storage, ticket_id)

            if already_closed:
                return f"{ticket.id} is already closed"
            return f"{ticket.id} → closed"

        except TicketNotFoundError as e:
            raise McpToolError(str(e))
        except AmbiguousIDError as e:
            raise McpToolError(str(e))
        except Exception as e:
            raise McpToolError(f"Failed to close ticket: {e}")

    @mcp.tool
    def bodega_note(
        ticket_id: Annotated[str, "Ticket ID"],
        text: Annotated[str, "Note text"],
    ) -> str:
        """Add a timestamped note to a ticket."""
        try:
            ticket = add_note(storage, ticket_id, text)
            return f"Added note to {ticket.id}"

        except TicketNotFoundError as e:
            raise McpToolError(str(e))
        except AmbiguousIDError as e:
            raise McpToolError(str(e))
        except Exception as e:
            raise McpToolError(f"Failed to add note: {e}")

    # ========================================================================
    # Medium Priority Tools - Enhanced Functionality
    # ========================================================================

    @mcp.tool
    def bodega_show(
        ticket_id: Annotated[str, "Ticket ID"],
    ) -> str:
        """Display detailed ticket information in formatted text."""
        try:
            ticket = query_tickets(storage, ticket_id=ticket_id)
            return format_ticket_detail(ticket, config)

        except TicketNotFoundError as e:
            raise McpToolError(str(e))
        except AmbiguousIDError as e:
            raise McpToolError(str(e))
        except Exception as e:
            raise McpToolError(f"Failed to show ticket: {e}")

    @mcp.tool
    def bodega_ready() -> str:
        """List open tickets with no unresolved dependencies, sorted by priority."""
        try:
            tickets = get_ready_tickets(storage)
            data = [ticket_to_dict(t) for t in tickets]
            return json.dumps(data, indent=2, default=str)

        except Exception as e:
            raise McpToolError(f"Failed to get ready tickets: {e}")

    @mcp.tool
    def bodega_dep(
        ticket_id: Annotated[
            str,
            "Ticket ID that has the dependency"
        ],
        blocker_id: Annotated[
            str,
            "Blocker ticket ID that must be closed first"
        ],
    ) -> str:
        """Add a dependency (BLOCKER blocks ID)."""
        try:
            ticket, blocker, already_dep = add_dependency(
                storage, ticket_id, blocker_id
            )

            if already_dep:
                return f"{ticket.id} already depends on {blocker.id}"
            return f"{ticket.id} now depends on {blocker.id}"

        except TicketNotFoundError as e:
            raise McpToolError(str(e))
        except AmbiguousIDError as e:
            raise McpToolError(str(e))
        except ValueError as e:
            raise McpToolError(str(e))
        except Exception as e:
            raise McpToolError(f"Failed to add dependency: {e}")

    return mcp


# ============================================================================
# Server Entry Points
# ============================================================================

def run_stdio_server(storage: TicketStorage, config: BodegaConfig) -> None:
    """Run the MCP server via stdio transport.

    Args:
        storage: TicketStorage instance
        config: BodegaConfig instance
    """
    mcp = create_mcp_server(storage, config)
    mcp.stdio()


def run_http_server(
    storage: TicketStorage,
    config: BodegaConfig,
    host: str = "127.0.0.1",
    port: int = 8000
) -> None:
    """Run the MCP server via HTTP transport.

    Args:
        storage: TicketStorage instance
        config: BodegaConfig instance
        host: Host to bind to
        port: Port to bind to
    """
    mcp = create_mcp_server(storage, config)
    mcp.serve(host, port)
