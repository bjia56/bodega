"""Core operations module - Shared business logic for CLI and MCP.

This module provides the core business logic for ticket operations,
separated from presentation (CLI) and protocol (MCP) concerns.
"""

from typing import Optional

from bodega.storage import TicketStorage
from bodega.config import BodegaConfig
from bodega.models.ticket import Ticket, TicketType, TicketStatus
from bodega.graph import DependencyGraph
from bodega.utils import get_git_user, now_utc


# ============================================================================
# Query Operations
# ============================================================================

def query_tickets(
    storage: TicketStorage,
    ticket_id: Optional[str] = None,
    status: Optional[TicketStatus] = None,
    ticket_type: Optional[str] = None,
    tag: Optional[str] = None,
    assignee: Optional[str] = None,
    priority: Optional[int] = None,
    include_closed: bool = False,
) -> list[Ticket] | Ticket:
    """Query tickets with filters.

    Args:
        storage: TicketStorage instance
        ticket_id: Query single ticket by ID (returns Ticket instead of list)
        status: Filter by status
        ticket_type: Filter by type
        tag: Filter by tag
        assignee: Filter by assignee
        priority: Filter by priority
        include_closed: Include closed tickets

    Returns:
        Single Ticket if ticket_id provided, otherwise list of Tickets

    Raises:
        TicketNotFoundError: Ticket not found
        AmbiguousIDError: Partial ID matches multiple tickets
    """
    if ticket_id:
        return storage.get(ticket_id)

    return list(storage.query(
        status=status,
        ticket_type=ticket_type,
        tag=tag,
        assignee=assignee,
        priority=priority,
        include_closed=include_closed,
    ))


def get_ready_tickets(storage: TicketStorage) -> list[Ticket]:
    """Get tickets ready to work on (no unresolved dependencies).

    Args:
        storage: TicketStorage instance

    Returns:
        List of ready tickets sorted by priority
    """
    graph = DependencyGraph(storage)
    tickets = graph.get_ready_tickets()
    tickets.sort(key=lambda t: (t.priority, t.created))
    return tickets


# ============================================================================
# Create Operations
# ============================================================================

def create_ticket(
    storage: TicketStorage,
    config: BodegaConfig,
    title: str,
    ticket_type: str = "task",
    priority: Optional[int] = None,
    assignee: Optional[str] = None,
    tags: Optional[list[str]] = None,
    description: Optional[str] = None,
    deps: Optional[list[str]] = None,
    parent: Optional[str] = None,
    external_ref: Optional[str] = None,
) -> tuple[Ticket, list[str]]:
    """Create a new ticket.

    Args:
        storage: TicketStorage instance
        config: BodegaConfig instance
        title: Ticket title
        ticket_type: Ticket type (bug, feature, task, epic, chore)
        priority: Priority (0-4)
        assignee: Assignee name
        tags: List of tags
        description: Ticket description
        deps: List of blocking ticket IDs
        parent: Parent ticket ID
        external_ref: External reference

    Returns:
        Tuple of (created ticket, list of missing dependency IDs)

    Raises:
        ValueError: Invalid ticket type or priority
    """
    # Validate ticket type
    if ticket_type not in ["bug", "feature", "task", "epic", "chore"]:
        raise ValueError(
            f"Invalid ticket type: {ticket_type}. "
            "Must be one of: bug, feature, task, epic, chore"
        )

    # Validate priority
    if priority is not None and (priority < 0 or priority > 4):
        raise ValueError(f"Invalid priority: {priority}. Must be 0-4")

    # Use defaults from config
    final_priority = priority if priority is not None else config.default_priority
    final_assignee = assignee or config.default_assignee

    # Create ticket
    ticket = Ticket(
        id="",  # Will be generated
        title=title,
        type=TicketType(ticket_type),
        status=TicketStatus.OPEN,
        priority=final_priority,
        assignee=final_assignee,
        tags=tags or [],
        deps=deps or [],
        parent=parent,
        external_ref=external_ref,
        description=description,
    )

    # Check for missing dependencies (warning, not error)
    missing_deps = []
    if deps:
        all_ids = storage.list_ids()
        missing_deps = [d for d in deps if d not in all_ids]

    created = storage.create(ticket)
    return created, missing_deps


# ============================================================================
# Lifecycle Operations
# ============================================================================

def start_ticket(
    storage: TicketStorage,
    config: BodegaConfig,
    ticket_id: str,
    assignee: Optional[str] = None,
) -> tuple[Ticket, bool]:
    """Start a ticket (set to in-progress).

    Args:
        storage: TicketStorage instance
        config: BodegaConfig instance
        ticket_id: Ticket ID (supports partial IDs)
        assignee: Update assignee (optional)

    Returns:
        Tuple of (updated ticket, was_already_in_progress)

    Raises:
        TicketNotFoundError: Ticket not found
        AmbiguousIDError: Partial ID matches multiple tickets
    """
    ticket = storage.get(ticket_id)
    already_in_progress = ticket.status == TicketStatus.IN_PROGRESS

    # Update status if not already in-progress
    if not already_in_progress:
        ticket.status = TicketStatus.IN_PROGRESS
        # Set assignee to git user if not already set and not explicitly provided
        if assignee is None and not ticket.assignee:
            ticket.assignee = config.default_assignee or get_git_user()

    # Update assignee if explicitly provided
    if assignee is not None:
        ticket.assignee = assignee if assignee else None

    storage.save(ticket)
    return ticket, already_in_progress


def close_ticket(storage: TicketStorage, ticket_id: str) -> tuple[Ticket, bool]:
    """Close a ticket.

    Args:
        storage: TicketStorage instance
        ticket_id: Ticket ID (supports partial IDs)

    Returns:
        Tuple of (updated ticket, was_already_closed)

    Raises:
        TicketNotFoundError: Ticket not found
        AmbiguousIDError: Partial ID matches multiple tickets
    """
    ticket = storage.get(ticket_id)
    already_closed = ticket.status == TicketStatus.CLOSED

    if not already_closed:
        ticket.status = TicketStatus.CLOSED
        storage.save(ticket)

    return ticket, already_closed


def reopen_ticket(storage: TicketStorage, ticket_id: str) -> tuple[Ticket, bool]:
    """Reopen a ticket (set to open).

    Args:
        storage: TicketStorage instance
        ticket_id: Ticket ID (supports partial IDs)

    Returns:
        Tuple of (updated ticket, was_already_open)

    Raises:
        TicketNotFoundError: Ticket not found
        AmbiguousIDError: Partial ID matches multiple tickets
    """
    ticket = storage.get(ticket_id)
    already_open = ticket.status == TicketStatus.OPEN

    if not already_open:
        ticket.status = TicketStatus.OPEN
        storage.save(ticket)

    return ticket, already_open


# ============================================================================
# Note Operations
# ============================================================================

def add_note(storage: TicketStorage, ticket_id: str, text: str) -> Ticket:
    """Add a timestamped note to a ticket.

    Args:
        storage: TicketStorage instance
        ticket_id: Ticket ID (supports partial IDs)
        text: Note text

    Returns:
        Updated ticket

    Raises:
        TicketNotFoundError: Ticket not found
        AmbiguousIDError: Partial ID matches multiple tickets
    """
    ticket = storage.get(ticket_id)
    ticket.add_note(text)
    storage.save(ticket)
    return ticket


# ============================================================================
# Edit Operations
# ============================================================================

def edit_ticket(
    storage: TicketStorage,
    ticket_id: str,
    title: Optional[str] = None,
    ticket_type: Optional[str] = None,
    priority: Optional[int] = None,
    assignee: Optional[str] = None,
    add_tags: Optional[list[str]] = None,
    remove_tags: Optional[list[str]] = None,
    description: Optional[str] = None,
) -> tuple[Ticket, bool]:
    """Edit ticket properties.

    Args:
        storage: TicketStorage instance
        ticket_id: Ticket ID (supports partial IDs)
        title: New title
        ticket_type: New type
        priority: New priority
        assignee: New assignee
        add_tags: Tags to add
        remove_tags: Tags to remove
        description: New description

    Returns:
        Tuple of (updated ticket, was_modified)

    Raises:
        TicketNotFoundError: Ticket not found
        AmbiguousIDError: Partial ID matches multiple tickets
        ValueError: Invalid type or priority
    """
    ticket = storage.get(ticket_id)
    modified = False

    if title is not None:
        ticket.title = title
        modified = True

    if ticket_type is not None:
        ticket.type = TicketType(ticket_type)
        modified = True

    if priority is not None:
        ticket.priority = priority
        modified = True

    if assignee is not None:
        ticket.assignee = assignee if assignee else None
        modified = True

    if add_tags:
        for t in add_tags:
            if t not in ticket.tags:
                ticket.tags.append(t)
        modified = True

    if remove_tags:
        for t in remove_tags:
            if t in ticket.tags:
                ticket.tags.remove(t)
        modified = True

    if description is not None:
        ticket.description = description
        modified = True

    if modified:
        ticket.updated = now_utc()
        storage.save(ticket)

    return ticket, modified


# ============================================================================
# Dependency Operations
# ============================================================================

def add_dependency(
    storage: TicketStorage,
    ticket_id: str,
    blocker_id: str,
) -> tuple[Ticket, Ticket, bool]:
    """Add a dependency (blocker blocks ticket).

    Args:
        storage: TicketStorage instance
        ticket_id: Ticket ID that has the dependency
        blocker_id: Blocker ticket ID that must be closed first

    Returns:
        Tuple of (ticket, blocker, was_already_dependency)

    Raises:
        TicketNotFoundError: Ticket not found
        AmbiguousIDError: Partial ID matches multiple tickets
        ValueError: Self-dependency or would create cycle
    """
    ticket = storage.get(ticket_id)
    blocker = storage.get(blocker_id)

    # Check for self-dependency
    if ticket.id == blocker.id:
        raise ValueError("Ticket cannot depend on itself")

    # Check if already a dependency
    if blocker.id in ticket.deps:
        return ticket, blocker, True

    # Check for cycle
    graph = DependencyGraph(storage)
    if graph.would_create_cycle(ticket.id, blocker.id):
        raise ValueError("Adding this dependency would create a cycle")

    # Add dependency
    ticket.deps.append(blocker.id)
    storage.save(ticket)
    return ticket, blocker, False


def remove_dependency(
    storage: TicketStorage,
    ticket_id: str,
    blocker_id: str,
) -> tuple[Ticket, Ticket, bool]:
    """Remove a dependency.

    Args:
        storage: TicketStorage instance
        ticket_id: Ticket ID that has the dependency
        blocker_id: Blocker ticket ID to remove

    Returns:
        Tuple of (ticket, blocker, was_dependency)

    Raises:
        TicketNotFoundError: Ticket not found
        AmbiguousIDError: Partial ID matches multiple tickets
    """
    ticket = storage.get(ticket_id)
    blocker = storage.get(blocker_id)

    if blocker.id not in ticket.deps:
        return ticket, blocker, False

    ticket.deps.remove(blocker.id)
    storage.save(ticket)
    return ticket, blocker, True
