"""Lifecycle commands - Manage ticket status transitions."""

import click

from bodega.commands.utils import pass_context, Context, require_repo
from bodega.models.ticket import TicketStatus
from bodega.errors import TicketNotFoundError, AmbiguousIDError


@click.command()
@click.argument("ticket_id", metavar="ID")
@pass_context
def start(ctx: Context, ticket_id: str):
    """
    Set ticket status to in-progress.

    Examples:

        bodega start bg-a1b2c3

        bodega start a1b  # Partial ID
    """
    storage = require_repo(ctx)

    try:
        ticket = storage.get(ticket_id)

        if ticket.status == TicketStatus.IN_PROGRESS:
            click.echo(f"{ticket.id} is already in-progress")
            return

        ticket.status = TicketStatus.IN_PROGRESS
        storage.save(ticket)
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
@click.argument("ticket_id", metavar="ID")
@pass_context
def close(ctx: Context, ticket_id: str):
    """
    Set ticket status to closed.

    Examples:

        bodega close bg-a1b2c3

        bodega close a1b
    """
    storage = require_repo(ctx)

    try:
        ticket = storage.get(ticket_id)

        if ticket.status == TicketStatus.CLOSED:
            click.echo(f"{ticket.id} is already closed")
            return

        ticket.status = TicketStatus.CLOSED
        storage.save(ticket)
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
@click.argument("ticket_id", metavar="ID")
@pass_context
def reopen(ctx: Context, ticket_id: str):
    """
    Set ticket status back to open.

    Examples:

        bodega reopen bg-a1b2c3
    """
    storage = require_repo(ctx)

    try:
        ticket = storage.get(ticket_id)

        if ticket.status == TicketStatus.OPEN:
            click.echo(f"{ticket.id} is already open")
            return

        ticket.status = TicketStatus.OPEN
        storage.save(ticket)
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
@click.argument("ticket_id", metavar="ID")
@pass_context
def status(ctx: Context, ticket_id: str):
    """
    Get ticket status.

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
