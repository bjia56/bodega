"""View commands - Display and edit tickets."""

import click
import subprocess
import json

from bodega.commands.utils import pass_context, Context, require_repo
from bodega.errors import TicketNotFoundError, AmbiguousIDError
from bodega.output import format_ticket_detail, ticket_to_dict
from bodega.operations import add_note, edit_ticket


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

        bodega show bg-a1b  # Partial ID

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
@click.option("--title", default=None, help="Update ticket title")
@click.option("--type", "-t", "ticket_type",
              type=click.Choice(["bug", "feature", "task", "epic", "chore"]),
              default=None, help="Update ticket type")
@click.option("--priority", "-p", type=click.IntRange(0, 4),
              default=None, help="Update priority (0=critical, 4=backlog)")
@click.option("--assignee", "-a", default=None, help="Update assignee name")
@click.option("--tag", multiple=True, help="Add tag (can be repeated)")
@click.option("--remove-tag", multiple=True, help="Remove tag (can be repeated)")
@click.option("--description", default=None, help="Update description text")
@pass_context
def edit(
    ctx: Context,
    ticket_id: str,
    title: str | None,
    ticket_type: str | None,
    priority: int | None,
    assignee: str | None,
    tag: tuple[str, ...],
    remove_tag: tuple[str, ...],
    description: str | None,
):
    """
    Edit ticket properties or open in $EDITOR

    If no options are provided, opens the ticket in $EDITOR for interactive editing.
    If any options are provided, updates those fields directly without opening an editor.

    Examples:

        bodega edit bg-a1b2c3  # Opens in editor

        bodega edit bg-a1b2c3 --title "New title"

        bodega edit bg-a1b2c3 -t bug -p 1

        bodega edit bg-a1b2c3 --tag urgent --tag api

        bodega edit bg-a1b2c3 --remove-tag old-tag

        bodega edit bg-a1b2c3 -a "John Doe" --description "Updated description"
    """
    storage = require_repo(ctx)

    try:
        ticket = storage.get(ticket_id)

        # Check if any modification options were provided
        has_modifications = any([
            title is not None,
            ticket_type is not None,
            priority is not None,
            assignee is not None,
            len(tag) > 0,
            len(remove_tag) > 0,
            description is not None,
        ])

        if has_modifications:
            # Apply modifications using operations module
            ticket, modified = edit_ticket(
                storage,
                ticket_id,
                title=title,
                ticket_type=ticket_type,
                priority=priority,
                assignee=assignee,
                add_tags=list(tag) if tag else None,
                remove_tags=list(remove_tag) if remove_tag else None,
                description=description,
            )

            if modified:
                click.echo(f"Updated {ticket.id}")
            else:
                click.echo(f"No changes made to {ticket.id}")

        else:
            # No options provided, open in editor
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

        bodega note bg-a1b "Discussed with team, moving forward"
    """
    storage = require_repo(ctx)

    try:
        ticket = add_note(storage, ticket_id, text)
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
