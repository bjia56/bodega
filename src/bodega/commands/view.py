"""View commands - Display and edit tickets."""

import click
import subprocess
import json

from bodega.commands.utils import pass_context, Context, require_repo
from bodega.errors import TicketNotFoundError, AmbiguousIDError
from bodega.output import format_ticket_detail, ticket_to_dict


@click.command()
@click.help_option("-h", "--help", help="Show this message and exit")
@click.argument("ticket_id", metavar="ID")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--raw", is_flag=True, help="Output raw markdown file")
@pass_context
def show(ctx: Context, ticket_id: str, as_json: bool, raw: bool):
    """
    Display ticket details

    Examples:

        bodega show bg-a1b2c3

        bodega show a1b  # Partial ID

        bodega show --json bg-a1b2c3

        bodega show --raw bg-a1b2c3
    """
    storage = require_repo(ctx)

    try:
        ticket = storage.get(ticket_id)

        if raw:
            # Output raw markdown file
            path = storage._ticket_path(ticket.id)
            click.echo(path.read_text())
        elif as_json:
            # Output as JSON
            data = ticket_to_dict(ticket)
            click.echo(json.dumps(data, indent=2, default=str))
        else:
            # Formatted display
            click.echo(format_ticket_detail(ticket, ctx.config))

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
def edit(ctx: Context, ticket_id: str):
    """
    Open ticket in $EDITOR for editing

    The ticket file is opened directly, allowing full control over
    all fields and content.

    Examples:

        bodega edit bg-a1b2c3

        EDITOR=code bodega edit bg-a1b2c3
    """
    storage = require_repo(ctx)

    try:
        ticket = storage.get(ticket_id)
        path = storage._ticket_path(ticket.id)

        # Open in editor
        editor = ctx.config.effective_editor
        result = subprocess.run([editor, str(path)])

        if result.returncode != 0:
            click.echo(f"Editor exited with code {result.returncode}", err=True)
            raise SystemExit(1)

        # Validate the edited file
        try:
            # Re-read to validate
            storage.get(ticket.id)
            click.echo(f"Saved {ticket.id}")
        except Exception as e:
            click.echo(f"Warning: File may have invalid format: {e}", err=True)

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
@click.argument("text")
@pass_context
def note(ctx: Context, ticket_id: str, text: str):
    """
    Add a timestamped note to a ticket

    Notes are appended to the ## Notes section with a timestamp.

    Examples:

        bodega note bg-a1b2c3 "Blocked waiting for API spec"

        bodega note a1b "Discussed with team, moving forward"
    """
    storage = require_repo(ctx)

    try:
        ticket = storage.get(ticket_id)

        # Add timestamped note
        ticket.add_note(text)

        storage.save(ticket)
        click.echo(f"Added note to {ticket.id}")

    except TicketNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except AmbiguousIDError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
