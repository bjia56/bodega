"""List commands - Query and display tickets."""

import click
import json
import sys

from bodega.commands.utils import pass_context, Context, require_repo
from bodega.models.ticket import TicketStatus
from bodega.operations import get_ready_tickets, query_tickets
from bodega.output import format_tickets, ticket_to_dict
from bodega.graph import DependencyGraph
from bodega.errors import TicketNotFoundError, AmbiguousIDError


@click.command(name="list")
@click.help_option("-h", "--help", help="Show this message and exit")
@click.option("--all", "-a", "include_all", is_flag=True,
              help="Include closed tickets")
@click.option("--status", "-s",
              type=click.Choice(["open", "in-progress", "closed"]),
              help="Filter by status")
@click.option("--type", "-t", "ticket_type",
              type=click.Choice(["bug", "feature", "task", "epic", "chore"]),
              help="Filter by type")
@click.option("--tag", help="Filter by tag")
@click.option("--assignee", help="Filter by assignee")
@click.option("--priority", "-p", type=click.IntRange(0, 4),
              help="Filter by priority")
@click.option("--sort",
              type=click.Choice(["priority", "created", "updated"]),
              default="priority", help="Sort by field")
@click.option("--reverse", "-r", is_flag=True, help="Reverse sort order")
@click.option("--format", "-f", "fmt",
              type=click.Choice(["json", "table", "compact", "ids"]),
              help="Output format")
@pass_context
def list_tickets(
    ctx: Context,
    include_all: bool,
    status: str | None,
    ticket_type: str | None,
    tag: str | None,
    assignee: str | None,
    priority: int | None,
    sort: str,
    reverse: bool,
    fmt: str | None,
):
    """
    List tickets with optional filters

    By default, shows only open and in-progress tickets.

    Examples:

        bodega list                      # All open tickets

        bodega list --all                # Include closed

        bodega list -s in-progress       # Filter by status

        bodega list -t bug --tag urgent  # Combined filters

        bodega list --sort created -r    # Sort by created, newest first
    """
    storage = require_repo(ctx)

    # Parse status filter
    status_filter = None
    if status:
        status_filter = TicketStatus(status)

    # Query tickets
    tickets = list(storage.query(
        status=status_filter,
        ticket_type=ticket_type,
        tag=tag,
        assignee=assignee,
        priority=priority,
        include_closed=include_all,
    ))

    # Sort
    sort_key = {
        "priority": lambda t: (t.priority, t.created),
        "created": lambda t: t.created,
        "updated": lambda t: t.updated,
    }[sort]

    tickets.sort(key=sort_key, reverse=reverse)

    # Format and output
    output = format_tickets(tickets, ctx.config, fmt)
    click.echo(output)


@click.command()
@click.help_option("-h", "--help", help="Show this message and exit")
@click.option("--tag", help="Filter by tag")
@pass_context
def ready(ctx: Context, tag: str | None = None):
    """
    List tickets that are ready to work on

    Shows open tickets with no unresolved dependencies.

    Examples:

        bodega ready
    """
    storage = require_repo(ctx)
    tickets = get_ready_tickets(storage)

    if tag:
        tickets = [t for t in tickets if tag in t.tags]

    output = format_tickets(tickets, ctx.config)
    click.echo(output)


@click.command()
@click.help_option("-h", "--help", help="Show this message and exit")
@pass_context
def blocked(ctx: Context):
    """
    List tickets that are blocked by dependencies

    Shows open tickets waiting on other tickets to close.

    Examples:

        bodega blocked
    """
    storage = require_repo(ctx)
    graph = DependencyGraph(storage)

    tickets = graph.get_blocked_tickets()
    tickets.sort(key=lambda t: (t.priority, t.created))

    if not tickets:
        click.echo("No blocked tickets.")
        return

    # Show blockers for each ticket
    for ticket in tickets:
        blockers = graph.get_blockers(ticket.id)
        blocker_str = ", ".join(blockers)
        click.echo(f"{ticket.id} [{ticket.type.value}/{ticket.priority}] {ticket.title}")
        click.echo(f"  Blocked by: {blocker_str}")


@click.command()
@click.help_option("-h", "--help", help="Show this message and exit")
@click.option("--count", "-n", default=10, help="Number of tickets to show")
@pass_context
def closed(ctx: Context, count: int):
    """
    List recently closed tickets

    Examples:

        bodega closed         # Last 10 closed

        bodega closed -n 20   # Last 20 closed
    """
    storage = require_repo(ctx)

    tickets = list(storage.query(
        status=TicketStatus.CLOSED,
        include_closed=True,
    ))

    # Sort by updated (most recently closed first)
    tickets.sort(key=lambda t: t.updated, reverse=True)
    tickets = tickets[:count]

    output = format_tickets(tickets, ctx.config)
    click.echo(output)


@click.command()
@click.help_option("-h", "--help", help="Show this message and exit")
@click.option("--all", "-a", "include_all", is_flag=True,
              help="Include closed tickets")
@click.option("--status", "-s",
              type=click.Choice(["open", "in-progress", "closed"]),
              help="Filter by status")
@click.option("--type", "-t", "ticket_type",
              type=click.Choice(["bug", "feature", "task", "epic", "chore"]),
              help="Filter by type")
@click.option("--tag", help="Filter by tag")
@click.option("--assignee", help="Filter by assignee")
@click.option("--priority", "-p", type=click.IntRange(0, 4),
              help="Filter by priority")
@click.option("--id", "ticket_id", help="Query single ticket by ID")
@click.option("--pretty/--no-pretty", default=None,
              help="Pretty-print JSON")
@pass_context
def query(
    ctx: Context,
    include_all: bool,
    status: str | None,
    ticket_type: str | None,
    tag: str | None,
    assignee: str | None,
    priority: int | None,
    ticket_id: str | None,
    pretty: bool | None,
):
    """
    Output tickets as JSON for scripting

    Examples:

        bodega query                           # All open as JSON

        bodega query --all                     # All tickets

        bodega query --id bg-a1b2c3            # Single ticket

        bodega query | jq '.[].title'          # Pipe to jq

        bodega query --no-pretty               # Compact JSON
    """
    storage = require_repo(ctx)

    # Default pretty to True if stdout is a TTY
    if pretty is None:
        pretty = sys.stdout.isatty()

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

        # Convert to dict
        if ticket_id:
            data = ticket_to_dict(result)  # result is single Ticket
        else:
            data = [ticket_to_dict(t) for t in result]  # result is list

        # Output JSON
        indent = 2 if pretty else None
        click.echo(json.dumps(data, indent=indent, default=str))

    except (TicketNotFoundError, AmbiguousIDError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
