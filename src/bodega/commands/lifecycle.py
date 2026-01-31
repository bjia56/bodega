"""Lifecycle commands - Manage ticket status transitions."""

import click

from bodega.commands.utils import pass_context, Context, require_repo
from bodega.models.ticket import TicketStatus
from bodega.errors import TicketNotFoundError, AmbiguousIDError


@click.command()
@click.help_option("-h", "--help", help="Show this message and exit")
@click.argument("ticket_id", metavar="ID")
@pass_context
def prep(ctx: Context, ticket_id: str):
    """
    Start prepping the order

    Marks the ticket as in-progress and sets the started timestamp.

    Examples:

        bodega prep bg-a1b2c3

        bodega prep bg-a1b  # Partial ID
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
@click.help_option("-h", "--help", help="Show this message and exit")
@click.argument("ticket_id", metavar="ID")
@pass_context
def bag(ctx: Context, ticket_id: str):
    """
    Bag it up - order complete!

    Marks the ticket as closed and sets the closed timestamp.

    Examples:

        bodega bag bg-a1b2c3

        bodega bag bg-a1b
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
@click.help_option("-h", "--help", help="Show this message and exit")
@click.argument("ticket_id", metavar="ID")
@pass_context
def remake(ctx: Context, ticket_id: str):
    """
    Remake an order

    Reopens a closed ticket by changing its status back to open.

    Examples:

        bodega remake bg-a1b2c3

        bodega remake a1b  # Partial ID
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
