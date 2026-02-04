"""Lifecycle commands - Manage ticket status transitions."""

import click

from bodega.commands.utils import pass_context, Context, require_repo
from bodega.errors import TicketNotFoundError, AmbiguousIDError
from bodega.operations import start_ticket, close_ticket, reopen_ticket


@click.command()
@click.help_option("-h", "--help", help="Show this message and exit")
@click.argument("ticket_id", metavar="ID")
@click.option("--assignee", "-a", default=None, help="Update assignee name")
@pass_context
def start(ctx: Context, ticket_id: str, assignee: str | None):
    """
    Set ticket status to in-progress

    Examples:

        bodega start bg-a1b2c3

        bodega start bg-a1b  # Partial ID

        bodega start bg-a1b2c3 -a "John Doe"  # Start and assign
    """
    storage = require_repo(ctx)

    try:
        ticket, already_in_progress = start_ticket(
            storage, ctx.config, ticket_id, assignee
        )

        if already_in_progress and assignee is None:
            click.echo(f"{ticket.id} is already in-progress")
            return

        if already_in_progress:
            click.echo(f"Updated {ticket.id}")
        else:
            click.echo(f"{ticket.id} → in-progress")

    except TicketNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except AmbiguousIDError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@click.command()
@click.help_option("-h", "--help", help="Show this message and exit")
@click.argument("ticket_id", metavar="ID")
@pass_context
def close(ctx: Context, ticket_id: str):
    """
    Set ticket status to closed

    Examples:

        bodega close bg-a1b2c3

        bodega close a1b
    """
    storage = require_repo(ctx)

    try:
        ticket, already_closed = close_ticket(storage, ticket_id)

        if already_closed:
            click.echo(f"{ticket.id} is already closed")
            return

        click.echo(f"{ticket.id} → closed")

    except TicketNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except AmbiguousIDError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@click.command()
@click.help_option("-h", "--help", help="Show this message and exit")
@click.argument("ticket_id", metavar="ID")
@pass_context
def reopen(ctx: Context, ticket_id: str):
    """
    Set ticket status back to open

    Examples:

        bodega reopen bg-a1b2c3
    """
    storage = require_repo(ctx)

    try:
        ticket, already_open = reopen_ticket(storage, ticket_id)

        if already_open:
            click.echo(f"{ticket.id} is already open")
            return

        click.echo(f"{ticket.id} → open")

    except TicketNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except AmbiguousIDError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@click.command()
@click.help_option("-h", "--help", help="Show this message and exit")
@click.argument("ticket_id", metavar="ID")
@pass_context
def status(ctx: Context, ticket_id: str):
    """
    Get ticket status

    Examples:

        bodega status bg-a1b2c3
    """
    storage = require_repo(ctx)

    try:
        ticket = storage.get(ticket_id)
        click.echo(ticket.status.value)

    except TicketNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except AmbiguousIDError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
